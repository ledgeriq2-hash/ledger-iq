from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import ADMIN, OWNER, require_roles
from app.schemas.common import BaseSchema
from app.models.tenant import Tenant

router = APIRouter(prefix="/dev")


class DevInfo(BaseSchema):
    status: str
    environment: str
    tenant_id: UUID


class DevTenantSummary(BaseSchema):
    id: UUID
    name: str
    slug: str


class DevTenantListResponse(BaseSchema):
    items: list[DevTenantSummary]


def _ensure_dev(settings) -> None:
    env = str(getattr(settings, "environment", "development") or "development").strip().lower()
    app_env = str(os.getenv("APP_ENV", "")).strip().lower()
    allow_flag = os.getenv("LEDGERIQ_ALLOW_DEV_ENDPOINTS") == "1"
    if env == "development" or app_env == "dev" or allow_flag:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev endpoints are not enabled")


@router.get("/info", response_model=DevInfo)
async def dev_info(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    settings=Depends(deps.get_settings),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN])),
):
    _ = session
    return DevInfo(
        status="ok",
        environment=str(getattr(settings, "environment", "unknown")),
        tenant_id=tenant_id,
    )


@router.get("/tenants", response_model=DevTenantListResponse)
async def list_tenants(
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    _ensure_dev(settings)
    result = await session.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    tenants = result.scalars().all()
    return DevTenantListResponse(
        items=[
            DevTenantSummary(id=tenant.id, name=tenant.name, slug=tenant.slug)
            for tenant in tenants
        ]
    )


@router.post("/reset-cache", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def reset_cache(
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN])),
):
    _ = tenant_id
    raise AppException(
        code="dev_not_implemented",
        message="Dev utilities are not enabled in this environment.",
        http_status=status.HTTP_501_NOT_IMPLEMENTED,
    )


@router.get("/trigger-500", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
async def trigger_server_error(settings=Depends(deps.get_settings)):
    _ensure_dev(settings)
    raise RuntimeError("triggered")


__all__ = ["router"]
