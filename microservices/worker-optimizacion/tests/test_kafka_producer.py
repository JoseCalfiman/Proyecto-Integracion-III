import json

from kafka_producer import (
    REPORT_TOPIC,
    build_producer,
    build_recommendation,
    publish_report,
)


def test_build_recommendation_has_expected_fields():
    report = build_recommendation()
    assert report["type"] == "optimization_report"
    assert "target_date" in report
    assert "projected_daily_cost" in report
    assert "estimated_savings" in report
    assert "recommendations" in report


def test_build_recommendation_records_are_valid():
    report = build_recommendation()
    for rec in report["recommendations"]:
        assert set(rec.keys()) >= {"equipment", "action", "window"}


def test_publish_report_serializes_json_and_produces():
    producer = build_producer()
    report = build_recommendation()
    returned = publish_report(report, producer=producer, topic="optimization.reports")

    assert returned is producer
    assert REPORT_TOPIC == "optimization.reports"


def test_report_is_json_serializable():
    payload = json.dumps(build_recommendation(), ensure_ascii=False)
    assert isinstance(payload, str)
    assert json.loads(payload)["type"] == "optimization_report"
