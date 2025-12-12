from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_event import ErrorEvent
from app.models.feedback import Feedback


async def cleanup_expired_data(
    session: AsyncSession,
    *,
    feedback_retention_days: int,
    error_event_retention_days: int,
) -> dict[str, str]:
    """Purge expired feedback and error events and commit within the service layer."""
    now = datetime.now(timezone.utc)
    feedback_cutoff = now - timedelta(days=max(feedback_retention_days, 1))
    error_cutoff = now - timedelta(days=max(error_event_retention_days, 1))

    await session.execute(Feedback.__table__.delete().where(Feedback.created_at < feedback_cutoff))
    await session.execute(ErrorEvent.__table__.delete().where(ErrorEvent.created_at < error_cutoff))
    await session.commit()

    return {
        "feedback_deleted_before": feedback_cutoff.isoformat(),
        "error_events_deleted_before": error_cutoff.isoformat(),
    }


__all__ = ["cleanup_expired_data"]
