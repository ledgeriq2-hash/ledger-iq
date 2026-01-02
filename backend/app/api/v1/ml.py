from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import ADMIN, OWNER, require_roles
from app.schemas.common import BaseSchema

router = APIRouter(prefix="/ml")


class MlStatus(BaseSchema):
    status: str
    tenant_id: UUID


def _raise_not_available() -> None:
    raise AppException(
        code="ml_not_available",
        message="ML ingestion is not enabled in this environment.",
        http_status=status.HTTP_501_NOT_IMPLEMENTED,
    )


@router.get("/status", response_model=MlStatus)
async def ml_status(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN])),
):
    _ = session
    return MlStatus(status="disabled", tenant_id=tenant_id)


@router.post("/predictions/ingest")
async def ingest_predictions(
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN])),
):
    _ = tenant_id
    _raise_not_available()


@router.post("/snapshots")
async def create_snapshot(
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN])),
):
    _ = tenant_id
    _raise_not_available()


__all__ = ["router"]
