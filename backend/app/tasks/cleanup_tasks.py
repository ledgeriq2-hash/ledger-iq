from __future__ import annotations

import asyncio

from celery import shared_task

from app.config import get_settings
from app.database import async_session_maker
from app.services.maintenance_service import cleanup_expired_data


@shared_task(name="app.tasks.cleanup_tasks.cleanup_expired")
def cleanup_expired() -> dict:
    async def _run():
        settings = get_settings()
        async with async_session_maker() as session:
            return await cleanup_expired_data(
                session,
                feedback_retention_days=settings.feedback_retention_days,
                error_event_retention_days=settings.error_event_retention_days,
            )

    return asyncio.run(_run())


__all__ = ["cleanup_expired"]
