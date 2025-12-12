from __future__ import annotations

from celery.schedules import crontab

beat_schedule = {
    "nightly-reports": {
        "task": "app.tasks.report_tasks.generate_daily_reports",
        "schedule": crontab(minute=0, hour=2),
    },
    "weekly-reports": {
        "task": "app.tasks.report_tasks.generate_weekly_reports",
        "schedule": crontab(minute=0, hour=3, day_of_week="mon"),
    },
    "nightly-cleanup": {
        "task": "app.tasks.cleanup_tasks.cleanup_expired",
        "schedule": crontab(minute=0, hour=4),
    },
    "recurring-invoices": {
        "task": "app.tasks.recurring_tasks.run_due_recurring_invoices",
        "schedule": crontab(minute="*/30"),
    },
}

__all__ = ["beat_schedule"]
