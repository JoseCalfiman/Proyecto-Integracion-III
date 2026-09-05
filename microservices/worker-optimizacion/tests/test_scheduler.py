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


def test_run_optimization_publishes_report(monkeypatch):
    published = {}

    def fake_publish(report):
        published["report"] = report

    monkeypatch.setattr(sched, "publish_report", fake_publish)
    report = sched.run_optimization()
    assert report["type"] == "optimization_report"
    assert published["report"]["estimated_savings"] == 2465.0
