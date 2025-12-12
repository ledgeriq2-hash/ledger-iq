from __future__ import annotations

from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_tenants(session: AsyncSession, tenant_id: UUID | None = None) -> Sequence[Tenant]:
    result = await session.execute(select(Tenant).where(Tenant.tenant_id == tenant_id))
    return result.scalars().all()


async def get_tenant(session: AsyncSession, tenant_id: UUID, scope_id: UUID | None = None) -> Tenant | None:
    result = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.tenant_id == scope_id)
    )
    return result.scalar_one_or_none()


async def get_tenant_by_slug(session: AsyncSession, slug: str, scope_id: UUID | None = None) -> Tenant | None:
    result = await session.execute(select(Tenant).where(Tenant.slug == slug, Tenant.tenant_id == scope_id))
    return result.scalar_one_or_none()


async def resolve_tenant(
    session: AsyncSession, identifier: str | UUID, scope_id: UUID | None = None
) -> Tenant | None:
    """
    Resolve a tenant by UUID or slug.

    Slugs are treated case-sensitively to match database constraints.
    """
    if isinstance(identifier, UUID):
        return await get_tenant(session, identifier, scope_id)
    try:
        tenant_uuid = UUID(str(identifier))
    except (TypeError, ValueError):
        return await get_tenant_by_slug(session, str(identifier), scope_id)
    return await get_tenant(session, tenant_uuid, scope_id)


async def create_tenant(session: AsyncSession, payload: Any, scope_id: UUID | None = None) -> Tenant:
    data = _to_dict(payload)
    tenant = Tenant(**data, tenant_id=scope_id)
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def update_tenant(
    session: AsyncSession, tenant_id: UUID, payload: Any, scope_id: UUID | None = None
) -> Tenant | None:
    tenant = await get_tenant(session, tenant_id, scope_id)
    if not tenant:
        return None
    data = _to_dict(payload, exclude_unset=True)
    for field, value in data.items():
        if field in {"id", "tenant_id"}:
            continue
        setattr(tenant, field, value)
    await session.commit()
    await session.refresh(tenant)
    return tenant


async def delete_tenant(session: AsyncSession, tenant_id: UUID, scope_id: UUID | None = None) -> bool:
    result = await session.execute(
        delete(Tenant).where(Tenant.id == tenant_id, Tenant.tenant_id == scope_id)
    )
    await session.commit()
    return result.rowcount > 0


async def initialize_tenant(
    session: AsyncSession,
    tenant_payload: Any,
    admin_payload: Any | None = None,
    roles_payload: list[Any] | None = None,
) -> dict[str, Any]:
    tenant = await create_tenant(session, tenant_payload, scope_id=None)

    created_roles = []
    if roles_payload:
        from app.services.role_service import create_role

        for role_payload in roles_payload:
            created_roles.append(await create_role(session, tenant.id, role_payload))

    admin_user = None
    if admin_payload:
        from app.services.user_service import create_user

        admin_user = await create_user(session, tenant.id, admin_payload)

    return {"tenant": tenant, "roles": created_roles, "admin_user": admin_user}


__all__ = [
    "list_tenants",
    "get_tenant",
    "get_tenant_by_slug",
    "resolve_tenant",
    "create_tenant",
    "update_tenant",
    "delete_tenant",
    "initialize_tenant",
]
