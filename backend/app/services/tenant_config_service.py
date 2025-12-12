from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.soft_launch import update_soft_launch_cache
from app.models.tenant import Tenant
from app.models.tenant_config import TenantConfig


async def _get_config(session: AsyncSession, tenant_id: UUID) -> TenantConfig | None:
    result = await session.execute(select(TenantConfig).where(TenantConfig.tenant_id == tenant_id))
    return result.scalar_one_or_none()


async def set_soft_launch(session: AsyncSession, tenant_id: UUID, enabled: bool) -> TenantConfig:
    result = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise ValueError("Tenant not found")

    config = await _get_config(session, tenant_id)
    if not config:
        config = TenantConfig(tenant_id=tenant_id, slug=tenant.slug, is_soft_launch=enabled)
        session.add(config)
    else:
        config.is_soft_launch = enabled
        config.slug = tenant.slug
    await session.commit()
    await session.refresh(config)
    update_soft_launch_cache(tenant.slug, enabled)
    if enabled:
        get_settings().soft_launch_enabled = True
    return config


async def is_soft_launch_enabled(session: AsyncSession, tenant_id: UUID) -> bool:
    config = await _get_config(session, tenant_id)
    return bool(config and config.is_soft_launch)


async def list_soft_launch_slugs(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(TenantConfig.slug).where(TenantConfig.is_soft_launch.is_(True), TenantConfig.slug.is_not(None))
    )
    return [slug for slug, in result.all()]


__all__ = ["set_soft_launch", "is_soft_launch_enabled", "list_soft_launch_slugs"]
