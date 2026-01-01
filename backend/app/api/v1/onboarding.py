from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import ADMIN, OWNER, require_roles
from app.schemas.common import BaseSchema
from app.services import onboarding_service

router = APIRouter(prefix="/onboarding")


class OnboardingPayload(BaseSchema):
    step: str | None = None
    profile_completed: bool | None = None
    sample_data_loaded: bool | None = None
    logo_url: str | None = None
    currency: str | None = None
    fiscal_year_start: str | None = None
    chart_preset: str | None = None


@router.get("/status")
async def onboarding_status(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    __ = Depends(deps.get_current_active_user),
):
    return await onboarding_service.get_status(session, tenant_id)


@router.post("/status")
async def update_onboarding_status(
    payload: OnboardingPayload,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    __ = Depends(deps.get_current_active_user),
    ___ = Depends(require_roles([OWNER, ADMIN])),
):
    return await onboarding_service.update_status(session, tenant_id, payload.model_dump(exclude_unset=True))


@router.post("/sample-data")
async def create_sample_data(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    __ = Depends(deps.get_current_active_user),
    ___ = Depends(require_roles([OWNER, ADMIN])),
):
    try:
        return await onboarding_service.create_sample_data(session, tenant_id)
    except AppException as exc:
        raise HTTPException(status_code=exc.http_status, detail=exc.message) from exc


__all__ = ["router"]
