import json
from types import SimpleNamespace

import pytest

import kafka_producer
from kafka_producer import HaccpAlertPublicationError, publish_haccp_alert


PAYLOAD = {
    "id_alert": 42,
    "id_chamber": "44444444-4444-4444-4444-444444444444",
    "id_prediction": 17,
    "alert_type": "haccp_violation",
    "severity": "high",
    "status": "active",
    "message": "Temperatura fuera de rango",
    "generation_date": "2026-10-19T12:00:00Z",
}


@pytest.fixture
def producer(monkeypatch):
    fake = SimpleNamespace(calls=[], pending=0, error=None, confirm=True,
                           immediate_error=None, flush_error=None)

    def produce(topic, value, *, key, callback):
        if fake.immediate_error:
            raise fake.immediate_error
        fake.calls.append((topic, value, key))
        fake.callback = callback

    def flush(timeout):
        fake.timeout = timeout
        if fake.flush_error:
            raise fake.flush_error
        if fake.confirm:
            fake.callback(fake.error, object())
        return fake.pending

    fake.produce = produce
    fake.flush = flush
    monkeypatch.setattr(kafka_producer, "Producer", lambda config: fake)
    return fake


def test_successful_delivery_has_complete_payload_and_chamber_key(producer):
    publish_haccp_alert(PAYLOAD)
    topic, value, key = producer.calls[0]
    assert topic == "haccp.alerts"
    assert json.loads(value.decode("utf-8")) == PAYLOAD
    assert key == PAYLOAD["id_chamber"].encode("utf-8")
    assert producer.timeout == kafka_producer.DELIVERY_TIMEOUT_SECONDS
    assert 0 < producer.timeout <= 30


def test_callback_error_is_failure_even_when_flush_returns_zero(producer):
    producer.error = "broker rejected message"
    with pytest.raises(HaccpAlertPublicationError, match="broker rejected"):
        publish_haccp_alert(PAYLOAD)


@pytest.mark.parametrize("confirm", [False, True])
def test_pending_messages_are_failure(producer, confirm):
    producer.pending = 1
    producer.confirm = confirm
    with pytest.raises(HaccpAlertPublicationError, match="pendientes"):
        publish_haccp_alert(PAYLOAD)


def test_missing_delivery_confirmation_is_failure(producer):
    producer.confirm = False
    with pytest.raises(HaccpAlertPublicationError, match="confirmó"):
        publish_haccp_alert(PAYLOAD)


@pytest.mark.parametrize("stage", ["immediate_error", "flush_error"])
def test_immediate_produce_or_flush_error_is_propagated(producer, stage):
    error = BufferError("queue unavailable")
    setattr(producer, stage, error)
    with pytest.raises(HaccpAlertPublicationError) as caught:
        publish_haccp_alert(PAYLOAD)
    assert caught.value.__cause__ is error


@pytest.mark.parametrize("field", list(PAYLOAD.keys() - {"alert_type"}))
def test_missing_required_field_is_not_published(producer, field):
    payload = PAYLOAD.copy()
    del payload[field]
    with pytest.raises(KeyError):
        publish_haccp_alert(payload)
    assert producer.calls == []
