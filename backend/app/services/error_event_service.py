from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error_event import ErrorEvent


async def record_error_event(
    session: AsyncSession,
    *,
    tenant_id: UUID | None,
    user_id: UUID | None,
    path: str,
    method: str,
    status_code: int,
    error_message: str,
) -> ErrorEvent:
    event = ErrorEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        path=path,
        method=method,
        status_code=status_code,
        error_message=error_message[:512],
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def fetch_errors_for_tenant(session: AsyncSession, tenant_id: UUID, limit: int = 50) -> Sequence[ErrorEvent]:
    result = await session.execute(
        select(ErrorEvent)
        .where(ErrorEvent.tenant_id == tenant_id)
        .order_by(ErrorEvent.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def fetch_recent_errors(session: AsyncSession, limit: int = 100) -> Sequence[ErrorEvent]:
    result = await session.execute(select(ErrorEvent).order_by(ErrorEvent.created_at.desc()).limit(limit))
    return result.scalars().all()


__all__ = ["record_error_event", "fetch_errors_for_tenant", "fetch_recent_errors"]
