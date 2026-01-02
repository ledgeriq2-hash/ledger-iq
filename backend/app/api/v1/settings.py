from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.schemas.settings import AppSettings, AppSettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/settings")


@router.get("/", response_model=AppSettings)
async def get_settings(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    return await settings_service.get_settings(session, tenant_id)


@router.put("/", response_model=AppSettings)
async def update_settings(
    payload: AppSettingsUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN])),
):
    try:
        return await settings_service.update_settings(session, tenant_id, payload)
    except ValueError as exc:
        raise AppException(
            code="tenant_not_found",
            message="Tenant not found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


__all__ = ["router"]
