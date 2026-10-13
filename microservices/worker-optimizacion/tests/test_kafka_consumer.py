import json

from buffer import ReadingsBuffer
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
