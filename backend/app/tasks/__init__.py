from __future__ import annotations

from app.tasks.celery_app import celery_app
from app.tasks.schedules import beat_schedule

__all__ = ["celery_app", "beat_schedule"]
