from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import PaginationParams, pagination_params
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.fx_revaluation import FXRevaluationRunCreate, FXRevaluationRunList, FXRevaluationRunRead
from app.services import fx_revaluation_service

router = APIRouter(prefix="/fx-revaluation")


@router.post("/run", response_model=FXRevaluationRunRead, status_code=status.HTTP_201_CREATED)
async def run_fx_revaluation(
    payload: FXRevaluationRunCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await fx_revaluation_service.run_revaluation(session, tenant_id, payload, actor_id=actor_id)


@router.get("/runs", response_model=FXRevaluationRunList)
async def list_fx_revaluation_runs(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    runs, total = await fx_revaluation_service.list_runs(
        session,
        tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return FXRevaluationRunList.from_results(items=runs, total=total, params=pagination)


@router.get("/runs/{run_id}", response_model=FXRevaluationRunRead)
async def get_fx_revaluation_run(
    run_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    run = await fx_revaluation_service.get_run(session, tenant_id, run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FX revaluation run not found")
    return run


__all__ = ["router"]
