from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import ADMIN, OWNER, require_roles
from app.schemas.common import BaseSchema

router = APIRouter(prefix="/dev")


class DevInfo(BaseSchema):
    status: str
    environment: str
    tenant_id: UUID


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


__all__ = ["router"]
