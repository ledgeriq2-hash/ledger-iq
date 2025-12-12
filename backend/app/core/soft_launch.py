from __future__ import annotations

from __future__ import annotations

from typing import Set

from sqlalchemy import select

from app.config import get_settings
from app.database import async_session_maker
from app.models.tenant import Tenant
from app.models.tenant_config import TenantConfig

_soft_launch_cache: Set[str] = set()


def _all_soft_launch_slugs() -> set[str]:
    settings = get_settings()
    configured = set(settings.soft_launch_tenant_slugs or [])
    return configured | set(_soft_launch_cache)


def is_soft_launch_tenant(tenant_slug: str | None) -> bool:
    """
    Return True when soft launch mode is enabled and the tenant slug is listed.

    Slugs are matched case-sensitively to mirror stored values.
    """
    settings = get_settings()
    if not settings.soft_launch_enabled:
        return False
    if not tenant_slug:
        return False
    return tenant_slug in _all_soft_launch_slugs()


async def refresh_soft_launch_slugs() -> list[str]:
    """Load soft-launch tenant slugs from TenantConfig into cache and settings."""
    global _soft_launch_cache
    async with async_session_maker() as session:
        result = await session.execute(
            select(Tenant.slug)
            .join(TenantConfig, TenantConfig.tenant_id == Tenant.id)
            .where(TenantConfig.is_soft_launch.is_(True))
        )
        slugs = [slug for slug, in result.all() if slug]
    _soft_launch_cache = set(slugs)
    settings = get_settings()
    merged = list({*slugs, *(settings.soft_launch_tenant_slugs or [])})
    settings.soft_launch_tenant_slugs = merged
    if merged:
        settings.soft_launch_enabled = True
    return merged


def update_soft_launch_cache(slug: str, enabled: bool) -> None:
    """Update in-memory cache when soft-launch state changes."""
    global _soft_launch_cache
    if not slug:
        return
    if enabled:
        _soft_launch_cache.add(slug)
    else:
        _soft_launch_cache.discard(slug)
    settings = get_settings()
    current = set(settings.soft_launch_tenant_slugs or [])
    if enabled:
        current.add(slug)
    else:
        current.discard(slug)
    settings.soft_launch_tenant_slugs = list(current)


__all__ = ["is_soft_launch_tenant", "refresh_soft_launch_slugs", "update_soft_launch_cache"]
