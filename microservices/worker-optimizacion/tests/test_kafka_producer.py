import json
from datetime import datetime

import pytest

from kafka_producer import (
    REPORT_TOPIC,
    build_recommendation,
    publish_report,
)


ID_CHAMBER = "44444444-4444-4444-4444-444444444444"


def _build_report(**overrides):
    report_data = {
        "id_chamber": ID_CHAMBER,
        "prediction_date": "2026-10-25",
        "predicted_kwh": 580.0,
        "price_kwh": 145.0,
    }
    report_data.update(overrides)
    return build_recommendation(**report_data)


def test_build_recommendation_has_expected_fields():
    report = _build_report()
    assert report["type"] == "optimization_report"
    assert report["id_chamber"] == ID_CHAMBER
    assert report["prediction_date"] == "2026-10-25"
    assert report["predicted_kwh"] == 580.0
    assert report["price_kwh"] == 145.0
    datetime.fromisoformat(report["generated_at"])
    assert "projected_daily_cost" in report
    assert "estimated_savings" in report
    assert "recommendations" in report


def test_build_recommendation_records_are_valid():
    report = _build_report()
    for rec in report["recommendations"]:
        assert set(rec.keys()) >= {"equipment", "action", "window"}


def test_build_recommendation_includes_savings_percentage():
    report = _build_report()
    projected_cost = report["projected_daily_cost"]

    assert report["recommendations"]
    for rec in report["recommendations"]:
        expected = round(rec["estimated_savings"] / projected_cost * 100, 2)
        assert rec["savings_percentage"] == expected


class FakeMessage:
    @staticmethod
    def topic():
        return REPORT_TOPIC

    @staticmethod
    def partition():
        return 2

    @staticmethod
    def offset():
        return 41


class FakeProducer:
    def __init__(self, error=None, pending=0):
        self.error = error
        self.pending = pending
        self.callback = None
        self.produced = None
        self.flushed = False

    def produce(self, topic, *, key, value, callback):
        self.produced = {
            "topic": topic,
            "key": key,
            "value": value,
        }
        self.callback = callback

    def poll(self, timeout):
        assert timeout == 0

    def flush(self, timeout):
        assert timeout > 0
        self.flushed = True
        if self.pending == 0:
            self.callback(self.error, FakeMessage())
        return self.pending


def test_publish_report_sends_chamber_key_and_verifies_delivery():
    producer = FakeProducer()
    report = _build_report()

    assert publish_report(report, producer=producer) is True

    assert producer.flushed is True
    assert producer.produced["topic"] == "optimization.reports"
    assert producer.produced["key"] == ID_CHAMBER.encode("utf-8")
    payload = json.loads(producer.produced["value"].decode("utf-8"))
    assert payload["id_chamber"] == ID_CHAMBER
    assert set(payload) >= {
        "prediction_date",
        "predicted_kwh",
        "price_kwh",
        "recommendations",
        "generated_at",
    }


def test_publish_report_raises_when_delivery_callback_reports_error():
    producer = FakeProducer(error=RuntimeError("broker unavailable"))

    with pytest.raises(RuntimeError, match="Kafka no entregó el reporte"):
        publish_report(_build_report(), producer=producer)


def test_publish_report_raises_when_delivery_times_out():
    producer = FakeProducer(pending=1)

    with pytest.raises(TimeoutError, match="no confirmó la entrega"):
        publish_report(_build_report(), producer=producer)


def test_publish_report_requires_chamber_key():
    report = _build_report()
    del report["id_chamber"]

    with pytest.raises(ValueError, match="id_chamber"):
        publish_report(report, producer=FakeProducer())


def test_report_is_json_serializable():
    payload = json.dumps(_build_report(), ensure_ascii=False)
    assert isinstance(payload, str)
    assert json.loads(payload)["type"] == "optimization_report"
