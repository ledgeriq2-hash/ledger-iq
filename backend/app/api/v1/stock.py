from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import PaginationParams, pagination_params
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.stock import StockBalanceOut, StockLedgerListOut
from app.services import stock_ledger_service

router = APIRouter(prefix="/stock")


@router.get("/balance", response_model=StockBalanceOut)
async def get_stock_balance(
    product_id: UUID = Query(...),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    balance = await stock_ledger_service.get_balance(session, tenant_id, product_id)
    return StockBalanceOut(product_id=product_id, base_quantity=balance)


@router.get("/ledger", response_model=StockLedgerListOut)
async def list_stock_ledger(
    product_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    moves, total = await stock_ledger_service.list_ledger(
        session,
        tenant_id,
        pagination,
        product_id=product_id,
    )
    return StockLedgerListOut.from_results(items=moves, total=total, params=pagination)


__all__ = ["router"]
