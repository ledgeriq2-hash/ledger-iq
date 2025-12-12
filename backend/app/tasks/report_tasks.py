from __future__ import annotations

from celery import shared_task

from app.tasks.celery_app import celery_app


@shared_task(name="app.tasks.report_tasks.generate_daily_reports")
def generate_daily_reports() -> dict:
    # Placeholder for real report generation logic
    return {"status": "ok", "type": "daily"}


@shared_task(name="app.tasks.report_tasks.generate_weekly_reports")
def generate_weekly_reports() -> dict:
    # Placeholder for real report generation logic
    return {"status": "ok", "type": "weekly"}


__all__ = ["generate_daily_reports", "generate_weekly_reports"]
