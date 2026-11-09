import json
from datetime import date

import numpy as np
import pandas as pd
import pytest

import scheduler as sched
from health import health
from kafka_producer import build_recommendation, publish_report
from optimizer import forecast_daily_consumption


@pytest.mark.parametrize(
    ("consumption", "expected_level"),
    [
        pytest.param([80.0] * 14, 80.0, id="consumo-estable"),
        pytest.param([10_000.0] * 14, 10_000.0, id="consumo-alto"),
        pytest.param([80.0] * 13 + [100_000.0], None, id="consumo-con-outlier"),
    ],
)
def test_forecast_scenarios_produce_finite_predictions(consumption, expected_level):
    history = pd.DataFrame(
        {
            "ds": pd.date_range("2026-01-01", periods=len(consumption), freq="D"),
            "y": consumption,
        }
    )

    forecast = forecast_daily_consumption(history, horizon=1)

    assert forecast is not None
    values = forecast[["yhat", "yhat_lower", "yhat_upper"]].to_numpy(dtype=float)
    assert np.isfinite(values).all()
    assert pd.Timestamp(forecast["ds"].iloc[-1]) == pd.Timestamp("2026-01-15")
    if expected_level is not None:
        assert forecast["yhat"].iloc[-1] == pytest.approx(expected_level, rel=0.01)


def test_insufficient_daily_consumption_does_not_create_forecast():
    one_day = pd.DataFrame(
        {"ds": [pd.Timestamp("2026-01-01")], "y": [80.0]}
    )

    assert forecast_daily_consumption(one_day, horizon=1) is None


def test_actionable_savings_are_generated_with_positive_amount_and_percentage():
    report = build_recommendation(
        id_chamber="44444444-4444-4444-4444-444444444444",
        prediction_date="2026-01-15",
        predicted_kwh=2_000.0,
        price_kwh=145.0,
    )

    assert report["recommendations"]
    assert report["estimated_savings"] > 0
    for recommendation in report["recommendations"]:
        assert recommendation["estimated_savings"] > 0
        assert recommendation["savings_percentage"] > 0
        assert recommendation["title"]
        assert recommendation["rationale"]


class _Message:
    @staticmethod
    def topic():
        return "optimization.reports"

    @staticmethod
    def partition():
        return 0

    @staticmethod
    def offset():
        return 1


class _CaptureProducer:
    def produce(self, topic, *, key, value, callback):
        self.topic = topic
        self.key = key
        self.value = value
        self.callback = callback

    def poll(self, timeout):
        pass

    def flush(self, timeout):
        self.callback(None, _Message())
        return 0


def test_zero_saving_recommendation_is_discarded_before_publish():
    report = build_recommendation(
        id_chamber="44444444-4444-4444-4444-444444444444",
        prediction_date="2026-01-15",
        predicted_kwh=0.0,
        price_kwh=145.0,
    )
    producer = _CaptureProducer()

    assert report["recommendations"] == []
    assert publish_report(report, producer=producer) is True
    published = json.loads(producer.value.decode("utf-8"))
    assert published["recommendations"] == []
    assert published["estimated_savings"] == 0


def test_scheduler_clamps_outlier_forecast_bounds_and_publishes_finite_report(
    monkeypatch,
):
    history = [
        {"date": date(2026, 1, day), "consumption_kwh": value}
        for day, value in enumerate([80.0] * 13 + [100_000.0], start=1)
    ]
    forecast = pd.DataFrame(
        {
            "ds": [pd.Timestamp("2026-01-15")],
            "yhat": [100_000.0],
            "yhat_lower": [-500.0],
            "yhat_upper": [120_000.0],
        }
    )
    published = []

    monkeypatch.setattr(sched.db, "validate_schema", lambda: True)
    monkeypatch.setattr(sched.db, "get_consumption_history", lambda days: history)
    monkeypatch.setattr(
        sched, "forecast_daily_consumption", lambda df, horizon: forecast
    )
    monkeypatch.setattr(
        sched, "get_current_quote", lambda: {"id_price": 7, "price_kwh": 145.0}
    )
    monkeypatch.setattr(sched.db, "save_report", lambda report: True)
    monkeypatch.setattr(sched, "publish_report", lambda report: published.append(report))
    health.reset()

    report = sched.run_optimization()

    assert report is not None
    assert report["predicted_kwh"] == 100_000.0
    assert report["predicted_kwh_lower"] == 0.0
    assert report["predicted_kwh_upper"] == 120_000.0
    assert np.isfinite(
        [
            report["predicted_kwh"],
            report["predicted_kwh_lower"],
            report["predicted_kwh_upper"],
            report["estimated_savings"],
        ]
    ).all()
    assert published == [report]
    assert all(
        recommendation["estimated_savings"] > 0
        and recommendation["savings_percentage"] > 0
        for recommendation in report["recommendations"]
    )
