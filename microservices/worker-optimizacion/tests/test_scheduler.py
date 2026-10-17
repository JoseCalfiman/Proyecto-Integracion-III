import logging

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import scheduler as sched
from buffer import ReadingsBuffer, normalize_reading
from health import health


def test_build_scheduler_returns_background_scheduler():
    scheduler = sched.build_scheduler()
    assert isinstance(scheduler, BackgroundScheduler)


def test_build_scheduler_schedules_interval_of_6_hours():
    scheduler = sched.build_scheduler()
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "optimization_job"
    assert isinstance(job.trigger, IntervalTrigger)
    assert job.trigger.interval.total_seconds() == 6 * 3600


def _fake_forecast():
    return pd.DataFrame(
        {
            "ds": [pd.Timestamp("2024-01-08")],
            "yhat": [580.0],
            "yhat_lower": [560.0],
            "yhat_upper": [600.0],
        }
    )


def test_run_optimization_persists_then_publishes(monkeypatch):
    calls = []

    monkeypatch.setattr(
        sched, "forecast_daily_consumption", lambda df, horizon: _fake_forecast()
    )
    monkeypatch.setattr(
        sched,
        "get_current_quote",
        lambda: {"id_price": 7, "price_kwh": 145.0},
    )
    monkeypatch.setattr(
        sched.db, "save_report", lambda report: calls.append(("save", report)) or True
    )
    monkeypatch.setattr(
        sched, "publish_report", lambda report: calls.append(("publish", report))
    )
    health.reset()

    report = sched.run_optimization()

    assert report["type"] == "optimization_report"
    assert report["target_date"] == "2024-01-08"
    assert report["forecasted_kwh"] == 580.0
    assert report["id_price"] == 7
    assert report["estimated_savings"] == 2465.0
    assert [name for name, _ in calls] == ["save", "publish"]
    assert calls[0][1] is report and calls[1][1] is report
    assert health.snapshot()["last_optimization_at"] is not None


def test_run_optimization_skips_without_data(monkeypatch):
    published = []
    health.reset()
    monkeypatch.setattr(
        sched, "forecast_daily_consumption", lambda df, horizon: None
    )
    monkeypatch.setattr(sched, "publish_report", lambda report: published.append(report))

    assert sched.run_optimization() is None
    assert published == []
    assert health.snapshot()["last_optimization_at"] is None


def test_worker_warns_and_does_not_invent_prediction_when_data_is_missing(
    monkeypatch, caplog
):
    buf = ReadingsBuffer()
    buf.add(normalize_reading({"ts": "2024-01-01T10:00:00Z", "consumption_kwh": 8.0}))
    assert normalize_reading({"consumption_kwh": 99.0}) is None

    saved = []
    published = []
    monkeypatch.setattr(sched.db, "save_report", lambda report: saved.append(report) or True)
    monkeypatch.setattr(sched, "publish_report", lambda report: published.append(report))
    monkeypatch.setattr(
        sched, "get_current_quote", lambda: {"id_price": 1, "price_kwh": 100.0}
    )

    with caplog.at_level(logging.WARNING):
        result = sched.run_optimization(buffer=buf)

    assert result is None
    assert saved == []
    assert published == []
    assert "datos insuficientes" in caplog.text
    assert "2024-01-08" not in caplog.text


def test_run_optimization_skips_without_price(monkeypatch):
    published = []
    monkeypatch.setattr(
        sched, "forecast_daily_consumption", lambda df, horizon: _fake_forecast()
    )
    monkeypatch.setattr(sched, "get_current_quote", lambda: None)
    monkeypatch.setattr(sched, "publish_report", lambda report: published.append(report))

    assert sched.run_optimization() is None
    assert published == []
