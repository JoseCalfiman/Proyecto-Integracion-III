import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

import scheduler as sched


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
    monkeypatch.setattr(sched, "get_current_price", lambda: 145.0)
    monkeypatch.setattr(
        sched.db, "save_report", lambda report: calls.append(("save", report)) or True
    )
    monkeypatch.setattr(
        sched, "publish_report", lambda report: calls.append(("publish", report))
    )

    report = sched.run_optimization()

    assert report["type"] == "optimization_report"
    assert report["target_date"] == "2024-01-08"
    assert report["forecasted_kwh"] == 580.0
    assert report["estimated_savings"] == 2465.0
    assert [name for name, _ in calls] == ["save", "publish"]
    assert calls[0][1] is report and calls[1][1] is report


def test_run_optimization_skips_without_data(monkeypatch):
    published = []
    monkeypatch.setattr(
        sched, "forecast_daily_consumption", lambda df, horizon: None
    )
    monkeypatch.setattr(sched, "publish_report", lambda report: published.append(report))

    assert sched.run_optimization() is None
    assert published == []
