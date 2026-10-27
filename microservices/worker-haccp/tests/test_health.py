import json
import threading
from datetime import datetime
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest
from confluent_kafka import KafkaError, KafkaException, TopicPartition

import kafka_consumer
from health import HealthHTTPServer, WorkerHealth, create_health_handler


CHAMBER_ID = "44444444-4444-4444-4444-444444444444"


def valid_anomaly_payload():
    return {
        "id_chamber": CHAMBER_ID,
        "id_prediction": 17,
        "temperature": 5.0,
        "remaining_time_min": 10.0,
        "severity": "critical",
        "risk_level": "MEDIO",
        "recorded_at": "2025-01-02T03:04:05+00:00",
    }


class FakeKafkaMessage:
    def __init__(self, value, offset):
        self._value = value
        self._offset = offset

    def value(self):
        return self._value

    def offset(self):
        return self._offset

    def topic(self):
        return kafka_consumer.TOPIC_ANOMALY

    def partition(self):
        return 0

    def error(self):
        return None


class FakeKafkaConsumer:
    def __init__(self):
        self.committed_offsets = []

    def commit(self, message, asynchronous):
        self.committed_offsets.append(message.offset())
        return [
            TopicPartition(
                message.topic(),
                message.partition(),
                message.offset() + 1,
            )
        ]


@pytest.fixture
def health_server():
    health = WorkerHealth()
    server = HealthHTTPServer(
        ("127.0.0.1", 0),
        create_health_handler(health),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield health, f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request_health(url):
    try:
        response = urlopen(f"{url}/health", timeout=1)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read())


def test_health_endpoint_reports_startup_then_kafka_availability(health_server):
    health, url = health_server

    status_code, payload = request_health(url)

    assert status_code == 503
    assert payload == {
        "status": "starting",
        "kafka_connected": False,
        "last_processed_at": None,
        "consumer_operational": False,
    }

    health.set_consumer_operational(True)
    health.set_kafka_connected(False)
    status_code, payload = request_health(url)

    assert status_code == 503
    assert payload["status"] == "unhealthy"
    assert payload["kafka_connected"] is False

    health.set_kafka_connected(True)
    status_code, payload = request_health(url)

    assert status_code == 200
    assert payload["status"] == "healthy"
    assert payload["kafka_connected"] is True
    assert payload["last_processed_at"] is None


def test_health_endpoint_reports_utc_last_processed_timestamp(health_server):
    health, url = health_server

    health.set_consumer_operational(True)
    health.set_kafka_connected(True)
    health.mark_processed()
    status_code, payload = request_health(url)

    assert status_code == 200
    timestamp = datetime.fromisoformat(payload["last_processed_at"].replace("Z", "+00:00"))
    assert timestamp.utcoffset().total_seconds() == 0


def test_health_endpoint_rejects_unknown_paths(health_server):
    _, url = health_server

    with pytest.raises(HTTPError) as error:
        urlopen(f"{url}/", timeout=1)

    assert error.value.code == 404


def test_liveness_endpoint_is_independent_of_kafka_readiness(health_server):
    health, url = health_server
    health.set_consumer_operational(True)
    health.set_kafka_connected(False)
    health.set_consumer_poll_error(True)

    with urlopen(f"{url}/live", timeout=1) as response:
        status_code = response.status
        payload = json.loads(response.read())

    assert status_code == 200
    assert payload == {
        "status": "alive",
        "consumer_operational": True,
    }


def test_consumer_poll_error_makes_readiness_unhealthy(health_server):
    health, url = health_server
    health.set_consumer_operational(True)
    health.set_kafka_connected(True)
    health.set_consumer_poll_error(True)

    status_code, payload = request_health(url)

    assert status_code == 503
    assert payload["status"] == "unhealthy"
    assert payload["consumer_operational"] is True


def test_kafka_health_probe_sets_connected_only_after_metadata_succeeds(
    monkeypatch,
):
    health = WorkerHealth()
    health.set_consumer_operational(True)
    stop_event = threading.Event()
    probe_results = iter([True, False])

    class FakeAdminClient:
        def __init__(self, config):
            assert config["bootstrap.servers"] == kafka_consumer.BOOTSTRAP_SERVERS

        def list_topics(self, timeout):
            assert timeout == kafka_consumer.KAFKA_HEALTH_CHECK_TIMEOUT_SECONDS
            if not next(probe_results):
                raise RuntimeError("broker unavailable")

    monkeypatch.setattr(kafka_consumer, "AdminClient", FakeAdminClient)
    monkeypatch.setattr(kafka_consumer, "KAFKA_HEALTH_CHECK_INTERVAL_SECONDS", 0)
    original_wait = stop_event.wait
    wait_count = 0
    snapshots = []

    def stop_after_two_checks(timeout):
        nonlocal wait_count
        wait_count += 1
        snapshots.append(health.snapshot())
        if wait_count == 2:
            stop_event.set()
            return True
        return original_wait(timeout)

    monkeypatch.setattr(stop_event, "wait", stop_after_two_checks)

    kafka_consumer._monitor_kafka_health(health, stop_event)

    assert wait_count == 2
    assert snapshots[0]["kafka_connected"] is True
    assert snapshots[0]["status"] == "healthy"
    assert health.snapshot()["kafka_connected"] is False
    assert health.snapshot()["status"] == "unhealthy"


@pytest.mark.parametrize(
    ("payload", "processed"),
    [
        ({"id_chamber": "bad"}, False),
        (valid_anomaly_payload(), True),
    ],
)
def test_message_handler_reports_only_successful_processing(
    monkeypatch, payload, processed
):
    def process(event):
        kafka_consumer._validate_anomaly_contract(event)

    monkeypatch.setattr(kafka_consumer, "process_alert", process)

    result = kafka_consumer._handle_kafka_message(
        FakeKafkaConsumer(),
        FakeKafkaMessage(json.dumps(payload).encode("utf-8"), 40),
    )

    assert result is processed


@pytest.mark.parametrize(
    "commit_behavior",
    ["no_result", "partition_error", "wrong_offset", "exception"],
)
def test_message_handler_does_not_report_success_without_offset_confirmation(
    monkeypatch, commit_behavior
):
    class CommitResultConsumer(FakeKafkaConsumer):
        def commit(self, message, asynchronous):
            if commit_behavior == "exception":
                raise KafkaException(KafkaError(KafkaError._TIMED_OUT))
            if commit_behavior == "no_result":
                return None
            if commit_behavior == "partition_error":
                return [
                    SimpleNamespace(
                        topic=message.topic(),
                        partition=message.partition(),
                        offset=message.offset() + 1,
                        error="broker rejected commit",
                    )
                ]
            return [
                TopicPartition(
                    message.topic(),
                    message.partition(),
                    message.offset() + 2,
                )
            ]

    monkeypatch.setattr(kafka_consumer, "process_alert", lambda event: None)

    with pytest.raises(
        (kafka_consumer.KafkaOffsetCommitError, KafkaException)
    ):
        kafka_consumer._handle_kafka_message(
            CommitResultConsumer(),
            FakeKafkaMessage(json.dumps(valid_anomaly_payload()).encode("utf-8"), 45),
        )


def test_consumer_updates_processed_timestamp_only_after_success(monkeypatch):
    health = WorkerHealth()
    health.set_kafka_connected(True)
    messages = [
        FakeKafkaMessage(b'{"id_chamber": "bad"}', 41),
        FakeKafkaMessage(
            json.dumps(valid_anomaly_payload()).encode("utf-8"), 42
        ),
    ]

    class FakeConsumer(FakeKafkaConsumer):
        def __init__(self, config):
            super().__init__()

        def subscribe(self, topics):
            assert topics == [kafka_consumer.TOPIC_ANOMALY]

        def poll(self, timeout):
            if messages:
                return messages.pop(0)
            raise RuntimeError("stop test consumer")

        def close(self):
            pass

    monkeypatch.setattr(kafka_consumer, "Consumer", FakeConsumer)
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: object())
    monkeypatch.setattr(kafka_consumer, "process_alert", lambda event: None)

    with pytest.raises(RuntimeError, match="stop test consumer"):
        kafka_consumer.consume_anomalies(health)

    assert health.snapshot()["last_processed_at"] is not None
    assert health.snapshot()["status"] == "unhealthy"


def test_consumer_does_not_update_timestamp_if_offset_commit_fails(monkeypatch):
    health = WorkerHealth()
    health.set_kafka_connected(True)

    class FailingCommitConsumer(FakeKafkaConsumer):
        def __init__(self, config):
            super().__init__()
            self.polled = False

        def subscribe(self, topics):
            pass

        def poll(self, timeout):
            if self.polled:
                raise RuntimeError("consumer stopped after commit failure")
            self.polled = True
            return FakeKafkaMessage(
                json.dumps(valid_anomaly_payload()).encode("utf-8"), 46
            )

        def commit(self, message, asynchronous):
            return [
                SimpleNamespace(
                    topic=message.topic(),
                    partition=message.partition(),
                    offset=message.offset() + 1,
                    error="broker rejected commit",
                )
            ]

        def close(self):
            pass

    monkeypatch.setattr(kafka_consumer, "Consumer", FailingCommitConsumer)
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: object())
    monkeypatch.setattr(kafka_consumer, "process_alert", lambda event: None)

    with pytest.raises(
        kafka_consumer.KafkaOffsetCommitError,
        match="broker rejected commit",
    ):
        kafka_consumer.consume_anomalies(health)

    assert health.snapshot()["last_processed_at"] is None


@pytest.mark.parametrize("failure", ["rejected", "processing"])
def test_consumer_does_not_update_timestamp_for_rejected_or_failed_event(
    monkeypatch, failure
):
    health = WorkerHealth()
    messages = [
        FakeKafkaMessage(
            b'{"id_chamber": "bad"}'
            if failure == "rejected"
            else json.dumps(valid_anomaly_payload()).encode("utf-8"),
            44,
        )
    ]

    class FakeConsumer(FakeKafkaConsumer):
        def __init__(self, config):
            super().__init__()

        def subscribe(self, topics):
            pass

        def poll(self, timeout):
            if messages:
                return messages.pop(0)
            raise RuntimeError("stop test consumer")

        def close(self):
            pass

    def fail_processing(payload):
        raise RuntimeError("processing failed")

    monkeypatch.setattr(kafka_consumer, "Consumer", FakeConsumer)
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: object())
    monkeypatch.setattr(kafka_consumer, "process_alert", fail_processing)

    with pytest.raises(RuntimeError, match="stop test consumer|processing failed"):
        kafka_consumer.consume_anomalies(health)

    assert health.snapshot()["last_processed_at"] is None


def test_health_http_remains_responsive_during_event_processing(monkeypatch):
    health = WorkerHealth()
    health.set_kafka_connected(True)
    stop_event = threading.Event()
    processing_started = threading.Event()
    release_processing = threading.Event()

    def slow_process(payload):
        processing_started.set()
        assert release_processing.wait(timeout=3)

    class FakeConsumer(FakeKafkaConsumer):
        def __init__(self, config):
            super().__init__()
            self.message_returned = False

        def subscribe(self, topics):
            pass

        def poll(self, timeout):
            if not self.message_returned:
                self.message_returned = True
                return FakeKafkaMessage(
                    json.dumps(valid_anomaly_payload()).encode("utf-8"), 43
                )
            return None

        def close(self):
            pass

    monkeypatch.setattr(kafka_consumer, "Consumer", FakeConsumer)
    monkeypatch.setattr(kafka_consumer, "get_engine", lambda: object())
    monkeypatch.setattr(kafka_consumer, "process_alert", slow_process)

    server = HealthHTTPServer(
        ("127.0.0.1", 0),
        create_health_handler(health),
    )
    http_thread = threading.Thread(target=server.serve_forever, daemon=True)
    consumer_thread = threading.Thread(
        target=kafka_consumer.consume_anomalies,
        args=(health, stop_event),
        daemon=True,
    )
    http_thread.start()
    consumer_thread.start()
    try:
        assert processing_started.wait(timeout=2)
        status_code, payload = request_health(
            f"http://127.0.0.1:{server.server_port}"
        )
        assert status_code == 200
        assert payload["status"] == "healthy"
    finally:
        release_processing.set()
        for _ in range(200):
            if health.snapshot()["last_processed_at"] is not None:
                break
            threading.Event().wait(0.01)
        stop_event.set()
        consumer_thread.join(timeout=3)
        server.shutdown()
        server.server_close()
        http_thread.join(timeout=2)

    assert not consumer_thread.is_alive()
    assert health.snapshot()["last_processed_at"] is not None


def test_run_worker_passes_and_sets_shared_stop_event(monkeypatch):
    captured = {}

    class FakeServer:
        def __init__(self, address, handler):
            captured["address"] = address
            self.shutdown_called = False
            self.closed = False

        def serve_forever(self):
            pass

        def shutdown(self):
            self.shutdown_called = True

        def server_close(self):
            self.closed = True

    class FakeThread:
        def __init__(self, target, **kwargs):
            self.target = target
            self.kwargs = kwargs
            captured.setdefault("threads", []).append(self)

        def start(self):
            pass

        def join(self, timeout=None):
            pass

    def stop_consumer(health, stop_event):
        captured["health"] = health
        captured["stop_event"] = stop_event

    server = FakeServer(("localhost", 0), None)
    monkeypatch.setattr(kafka_consumer, "HEALTH_PORT_ENV", "TEST_HEALTH_PORT")
    monkeypatch.setenv("TEST_HEALTH_PORT", "8080")
    monkeypatch.setattr(kafka_consumer, "HealthHTTPServer", lambda *args: server)
    monkeypatch.setattr(kafka_consumer, "Thread", FakeThread)
    monkeypatch.setattr(kafka_consumer, "consume_anomalies", stop_consumer)

    kafka_consumer.run_worker()

    assert captured["threads"][1].kwargs["args"] == (
        captured["health"],
        captured["stop_event"],
    )
    assert captured["stop_event"].is_set()
    assert server.shutdown_called
    assert server.closed
