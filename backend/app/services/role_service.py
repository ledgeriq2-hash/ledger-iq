from __future__ import annotations

from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_roles(session: AsyncSession, tenant_id: UUID | None) -> Sequence[Role]:
    result = await session.execute(select(Role).where(Role.tenant_id == tenant_id))
    return result.scalars().all()


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
