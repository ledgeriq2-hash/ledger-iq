from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.permissions import ensure_permission
from app.models.user import User


async def require_permission(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    actor_id: UUID | None,
    permission_code: str,
    message: str = "Insufficient permissions",
) -> User:
    if actor_id is None:
        raise AppException(
            code="permission_denied",
            message=message,
            http_status=status.HTTP_403_FORBIDDEN,
        )
    result = await session.execute(
        select(User).where(User.id == actor_id, User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise AppException(
            code="permission_denied",
            message=message,
            http_status=status.HTTP_403_FORBIDDEN,
        )
    ensure_permission(user, permission_code, message=message)
    return user


__all__ = ["require_permission"]
