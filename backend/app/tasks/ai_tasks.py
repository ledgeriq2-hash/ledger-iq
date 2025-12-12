from __future__ import annotations

from celery import shared_task

from app.tasks.celery_app import celery_app
from app.ai.forecast import generate_forecast
from app.ai.anomaly import detect_anomalies


@shared_task(name="app.tasks.ai_tasks.generate_forecast_task")
def generate_forecast_task(payload: dict) -> dict:
    return generate_forecast(payload)


@shared_task(name="app.tasks.ai_tasks.detect_anomalies_task")
def detect_anomalies_task(payload: dict) -> dict:
    return detect_anomalies(payload)


__all__ = ["generate_forecast_task", "detect_anomalies_task"]
