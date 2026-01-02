from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import ADMIN, OWNER, require_roles
from app.schemas.common import BaseSchema

router = APIRouter(prefix="/ml")


class MlStatus(BaseSchema):
    status: str
    tenant_id: UUID


class MlLatestPrediction(BaseSchema):
    prediction_type: str | None = None
    model_version: str | None = None
    run_id: UUID | None = None
    data_snapshot_id: UUID | None = None
    created_at: datetime | None = None
    series: dict | None = None
    metrics: dict | None = None


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


@router.get("/predictions/latest", response_model=MlLatestPrediction | None)
async def latest_prediction(
    prediction_type: str | None = Query(default=None),
    model_version: str | None = Query(default=None),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN])),
):
    _ = prediction_type, model_version, tenant_id
    return None


__all__ = ["router"]
