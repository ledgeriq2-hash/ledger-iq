from __future__ import annotations

from celery import Celery

from app.config import get_settings
from app.tasks.schedules import beat_schedule

settings = get_settings()

broker_url = settings.redis_url
backend_url = settings.redis_url

celery_app = Celery(
    "ledgeriq",
    broker=broker_url,
    backend=backend_url,
    include=[
        "app.tasks.report_tasks",
        "app.tasks.ai_tasks",
        "app.tasks.cleanup_tasks",
        "app.tasks.recurring_tasks",
        "app.tasks.gdpr_tasks",
    ],
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_routes = {"app.tasks.*": {"queue": "default"}}
celery_app.conf.beat_schedule = beat_schedule

__all__ = ["celery_app"]
