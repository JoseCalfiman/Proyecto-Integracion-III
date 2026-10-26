import json
import threading

from buffer import ReadingsBuffer
import kafka_consumer
from kafka_consumer import process_message


def test_process_message_feeds_buffer():
    buf = ReadingsBuffer()
    raw = json.dumps(
        {"timestamp": "2024-01-01T00:00:00Z", "consumption_kwh": 5.0}
    ).encode("utf-8")

    reading = process_message(raw, buffer=buf)

    assert reading is not None
    assert len(buf) == 1
    assert buf.snapshot()[0]["consumption_kwh"] == 5.0


def test_process_message_invalid_json_returns_none():
    buf = ReadingsBuffer()
    assert process_message(b"{not-json", buffer=buf) is None
    assert len(buf) == 0


def test_consume_retries_after_transient_kafka_error(monkeypatch):
    class TransientError:
        def code(self):
            return 1

        def fatal(self):
            return False

        def __str__(self):
            return "broker unavailable"

    class ErrorMessage:
        @staticmethod
        def error():
            return TransientError()

    class FakeConsumer:
        def __init__(self):
            self.poll_count = 0

        def subscribe(self, topics):
            self.topics = topics

        def poll(self, timeout):
            self.poll_count += 1
            if self.poll_count == 1:
                return ErrorMessage()
            stop_event.set()
            return None

    stop_event = threading.Event()
    consumer = FakeConsumer()
    monkeypatch.setattr(kafka_consumer.time, "sleep", lambda seconds: None)

    kafka_consumer.consume(consumer, stop_event, ReadingsBuffer())

    assert consumer.poll_count == 2
    assert consumer.topics == [kafka_consumer.TOPIC]
