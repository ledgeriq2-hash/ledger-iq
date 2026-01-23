from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import PaginationParams, pagination_params
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.stock import StockBalanceOut, StockMoveCreate, StockMoveListOut, StockMoveOut
from app.services import stock_service

router = APIRouter(prefix="/stock")


@router.get("/moves", response_model=StockMoveListOut)
async def list_stock_moves(
    product_id: UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    reference_type: str | None = Query(default=None),
    reference_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    moves, total = await stock_service.list_moves(
        session,
        tenant_id,
        pagination,
        product_id=product_id,
        date_from=date_from,
        date_to=date_to,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    return StockMoveListOut.from_results(items=moves, total=total, params=pagination)


@router.post("/moves", response_model=StockMoveOut, status_code=status.HTTP_201_CREATED)
async def create_stock_move(
    payload: StockMoveCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    _ = request
    move, _balance = await stock_service.record_move(session, tenant_id, payload)
    return move


@router.get("/balances/{product_id}", response_model=StockBalanceOut)
async def get_stock_balance(
    product_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    return await stock_service.get_balance(session, tenant_id, product_id)


__all__ = ["router"]
