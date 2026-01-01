from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_notifications(session: AsyncSession, tenant_id: UUID) -> Sequence[Notification]:
    result = await session.execute(select(Notification).where(Notification.tenant_id == tenant_id))
    return result.scalars().all()


async def get_notification(
    session: AsyncSession, tenant_id: UUID, notification_id: UUID
) -> Notification | None:
    result = await session.execute(
        select(Notification).where(Notification.id == notification_id, Notification.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_notification(session: AsyncSession, tenant_id: UUID, payload: Any) -> Notification:
    data = _to_dict(payload)
    notification = Notification(**data, tenant_id=tenant_id)
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification


async def update_notification(
    session: AsyncSession, tenant_id: UUID, notification_id: UUID, payload: Any
) -> Notification | None:
    notification = await get_notification(session, tenant_id, notification_id)
    if not notification:
        return None
    data = _to_dict(payload, exclude_unset=True)
    for field, value in data.items():
        if field in {"id", "tenant_id"}:
            continue
        setattr(notification, field, value)
    await session.commit()
    await session.refresh(notification)
    return notification


async def mark_notification_read(
    session: AsyncSession, tenant_id: UUID, notification_id: UUID, read: bool = True
) -> Notification | None:
    notification = await get_notification(session, tenant_id, notification_id)
    if not notification:
        return None
    notification.is_read = read
    notification.read_at = datetime.now(UTC) if read else None
    await session.commit()
    await session.refresh(notification)
    return notification


async def delete_notification(session: AsyncSession, tenant_id: UUID, notification_id: UUID) -> bool:
    result = await session.execute(
        delete(Notification).where(Notification.id == notification_id, Notification.tenant_id == tenant_id)
    )
    await session.commit()
    return result.rowcount > 0


__all__ = [
    "list_notifications",
    "get_notification",
    "create_notification",
    "update_notification",
    "mark_notification_read",
    "delete_notification",
]
