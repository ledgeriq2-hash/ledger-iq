from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.utils.pagination import normalize_pagination


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_roles(
    session: AsyncSession,
    tenant_id: UUID | None,
    page: int | None = None,
    page_size: int | None = None,
    include_total: bool = False,
) -> Sequence[Role] | tuple[list[Role], int]:
    base = select(Role).where(Role.tenant_id == tenant_id).order_by(Role.created_at.desc())
    if page is None and page_size is None and not include_total:
        result = await session.execute(base)
        return result.scalars().all()
    page, page_size, offset = normalize_pagination(page, page_size)
    result = await session.execute(base.offset(offset).limit(page_size))
    items = result.scalars().all()
    if not include_total:
        return items
    total = await session.scalar(select(func.count()).select_from(Role).where(Role.tenant_id == tenant_id)) or 0
    return items, total


async def get_role(session: AsyncSession, tenant_id: UUID | None, role_id: UUID) -> Role | None:
    result = await session.execute(
        select(Role).where(Role.id == role_id, Role.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_role(session: AsyncSession, tenant_id: UUID | None, payload: Any) -> Role:
    data = _to_dict(payload)
    role = Role(**data, tenant_id=tenant_id)
    session.add(role)
    await session.commit()
    await session.refresh(role)
    return role


async def update_role(
    session: AsyncSession, tenant_id: UUID | None, role_id: UUID, payload: Any
) -> Role | None:
    role = await get_role(session, tenant_id, role_id)
    if not role:
        return None
    data = _to_dict(payload, exclude_unset=True)
    for field, value in data.items():
        if field in {"id", "tenant_id"}:
            continue
        setattr(role, field, value)
    await session.commit()
    await session.refresh(role)
    return role


async def delete_role(session: AsyncSession, tenant_id: UUID | None, role_id: UUID) -> bool:
    result = await session.execute(delete(Role).where(Role.id == role_id, Role.tenant_id == tenant_id))
    await session.commit()
    return result.rowcount > 0


__all__ = ["list_roles", "get_role", "create_role", "update_role", "delete_role"]
