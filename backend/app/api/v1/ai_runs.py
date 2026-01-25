from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.ai_run import AiRun
from app.models.user import User
from app.schemas.ai_runs_v1 import AiRunCreateRequest, AiRunMetaV1, AiRunResponse
from app.schemas.common import BaseSchema
from app.services import ai_runs_service

router = APIRouter(prefix="/ai/runs")


class AiRunRevokeRequest(BaseSchema):
    reason: str | None = None


def _run_meta_from_model(run: AiRun) -> AiRunMetaV1:
    return AiRunMetaV1(
        model_name=run.model_name,
        model_version=run.model_version,
        dataset_fingerprint=run.dataset_fingerprint,
        created_at=run.created_at,
        created_by=run.created_by,
        date_from=run.date_from,
        date_to=run.date_to,
        scenario=run.scenario,
    )


def _run_response_from_model(run: AiRun) -> AiRunResponse:
    return AiRunResponse(
        id=run.id,
        client_id=run.client_id,
        schema_version=run.schema_version,
        run_meta=_run_meta_from_model(run),
        status=run.status,
        payload_hash=run.payload_hash,
        payload_json=run.payload_json,
        signature=run.signature,
        created_at=run.created_at,
        created_by=run.created_by,
        revoked_at=run.revoked_at,
        revoked_by=run.revoked_by,
        revoke_reason=run.revoke_reason,
        superseded_by_run_id=run.superseded_by_run_id,
    )


def _actor_identity(user: User | deps.DevUser) -> str | None:
    actor_id = getattr(user, "id", None)
    return str(actor_id) if actor_id else None


@router.post("", response_model=AiRunResponse, status_code=status.HTTP_201_CREATED)
async def create_ai_run(
    payload: AiRunCreateRequest,
    session: AsyncSession = Depends(deps.get_db),
    client_id: UUID = Depends(deps.get_current_tenant),
    _: User | deps.DevUser = Depends(deps.get_current_active_user),
):
    run = await ai_runs_service.create_run(db=session, client_id=client_id, req=payload)
    return _run_response_from_model(run)


@router.get("", response_model=list[AiRunResponse])
async def list_ai_runs(
    status_filter: str | None = Query(default=None, alias="status"),
    scenario: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(deps.get_db),
    client_id: UUID = Depends(deps.get_current_tenant),
    _: User | deps.DevUser = Depends(deps.get_current_active_user),
):
    runs = await ai_runs_service.list_runs(
        db=session,
        client_id=client_id,
        status=status_filter,
        scenario=scenario,
        limit=limit,
        offset=offset,
    )
    return [_run_response_from_model(run) for run in runs]


@router.get("/{run_id}", response_model=AiRunResponse)
async def get_ai_run(
    run_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    client_id: UUID = Depends(deps.get_current_tenant),
    _: User | deps.DevUser = Depends(deps.get_current_active_user),
):
    run = await ai_runs_service.get_run(db=session, client_id=client_id, run_id=run_id)
    return _run_response_from_model(run)


@router.post("/{run_id}/revoke", response_model=AiRunResponse)
async def revoke_ai_run(
    run_id: UUID,
    payload: AiRunRevokeRequest,
    session: AsyncSession = Depends(deps.get_db),
    client_id: UUID = Depends(deps.get_current_tenant),
    actor: User | deps.DevUser = Depends(deps.get_current_active_user),
):
    run = await ai_runs_service.revoke_run(
        db=session,
        client_id=client_id,
        run_id=run_id,
        revoked_by=_actor_identity(actor),
        reason=payload.reason,
    )
    return _run_response_from_model(run)


__all__ = ["router"]
