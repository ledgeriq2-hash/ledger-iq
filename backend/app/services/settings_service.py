from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.schemas.settings import AppSettings, AppSettingsUpdate


DEFAULT_PRIMARY = "#4EB7B3"
DEFAULT_SECONDARY = "#C1E3E3"
APP_SETTINGS_KEY = "app_settings"


def _merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _default_settings() -> AppSettings:
    return AppSettings(
        feature_toggles={
            "ai": True,
            "suppliers": True,
            "workers": True,
            "debts": True,
            "invoices": True,
            "portal": True,
            "pages": {
                "dashboard_ai": True,
                "dashboard_suppliers": True,
                "dashboard_workers": True,
                "dashboard_debts": True,
                "dashboard_invoices": True,
            },
        },
        currency="USD",
        taxes={"enabled": False, "rate": 0},
        field_labels={},
        theme={"primary": DEFAULT_PRIMARY, "secondary": DEFAULT_SECONDARY, "mode": "light"},
    )


def _enforce_palette(theme: dict[str, Any] | None) -> dict[str, Any]:
    base = {"primary": DEFAULT_PRIMARY, "secondary": DEFAULT_SECONDARY, "mode": "light"}
    if not isinstance(theme, dict):
        return base
    out = {**base, **theme}
    if str(out.get("primary") or "").upper() not in {DEFAULT_PRIMARY}:
        out["primary"] = DEFAULT_PRIMARY
    if str(out.get("secondary") or "").upper() not in {DEFAULT_SECONDARY}:
        out["secondary"] = DEFAULT_SECONDARY
    mode = str(out.get("mode") or "light").lower()
    out["mode"] = "dark" if mode == "dark" else "light"
    return out


async def get_settings(session: AsyncSession, tenant_id: UUID) -> AppSettings:
    tenant = await session.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        return _default_settings()

    root = tenant.settings_json if isinstance(tenant.settings_json, dict) else {}
    stored = root.get(APP_SETTINGS_KEY) if isinstance(root.get(APP_SETTINGS_KEY), dict) else {}
    defaults = _default_settings().model_dump()
    merged = _merge(defaults, stored)
    merged["theme"] = _enforce_palette(merged.get("theme"))
    return AppSettings.model_validate(merged)


async def update_settings(session: AsyncSession, tenant_id: UUID, payload: AppSettingsUpdate) -> AppSettings:
    tenant = await session.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        raise ValueError("tenant not found")

    root = tenant.settings_json if isinstance(tenant.settings_json, dict) else {}
    stored = root.get(APP_SETTINGS_KEY) if isinstance(root.get(APP_SETTINGS_KEY), dict) else {}
    defaults = _default_settings().model_dump()
    base = _merge(defaults, stored)

    update = payload.model_dump(exclude_unset=True)
    if "theme" in update:
        update["theme"] = _enforce_palette(update.get("theme"))

    next_settings = _merge(base, update)
    next_settings["theme"] = _enforce_palette(next_settings.get("theme"))
    validated = AppSettings.model_validate(next_settings)

    root[APP_SETTINGS_KEY] = validated.model_dump()
    tenant.settings_json = root
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return validated


__all__ = ["get_settings", "update_settings"]
