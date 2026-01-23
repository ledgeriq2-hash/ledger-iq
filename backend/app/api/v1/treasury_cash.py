from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, require_roles
from app.models.treasury_cash_transaction import CashTransactionStatus, CashTransactionType
from app.schemas.treasury_cash import (
    CashAccountCreate,
    CashAccountList,
    CashAccountPublic,
    CashTransactionCreate,
    CashTransactionList,
    CashTransactionPublic,
    CashTransactionReverseRequest,
)
from app.services import treasury_cash_service

router = APIRouter(prefix="/treasury", dependencies=[Depends(require_roles([OWNER, ADMIN, ACCOUNTANT]))])


@router.post("/cash-accounts", response_model=CashAccountPublic, status_code=status.HTTP_201_CREATED)
async def create_cash_account(
    payload: CashAccountCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    return await treasury_cash_service.create_cash_account(session, tenant_id, payload, actor_id=actor_id)


@router.get("/cash-accounts", response_model=CashAccountList)
async def list_cash_accounts(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    items = await treasury_cash_service.list_cash_accounts(session, tenant_id)
    return CashAccountList(items=list(items))


@router.post("/transactions", response_model=CashTransactionPublic, status_code=status.HTTP_201_CREATED)
async def create_cash_transaction(
    payload: CashTransactionCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    return await treasury_cash_service.create_cash_transaction(session, tenant_id, payload, actor_id=actor_id)


@router.get("/transactions", response_model=CashTransactionList)
async def list_cash_transactions(
    transaction_type: CashTransactionType | None = Query(None),
    status_filter: CashTransactionStatus | None = Query(None, alias="status"),
    cash_account_id: UUID | None = Query(None),
    counterparty_account_id: UUID | None = Query(None),
    from_cash_account_id: UUID | None = Query(None),
    to_cash_account_id: UUID | None = Query(None),
    posting_date_start: date | None = Query(None),
    posting_date_end: date | None = Query(None),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    items = await treasury_cash_service.list_cash_transactions(
        session,
        tenant_id,
        transaction_type=transaction_type,
        status=status_filter,
        cash_account_id=cash_account_id,
        counterparty_account_id=counterparty_account_id,
        from_cash_account_id=from_cash_account_id,
        to_cash_account_id=to_cash_account_id,
        posting_date_start=posting_date_start,
        posting_date_end=posting_date_end,
    )
    return CashTransactionList(items=list(items))


@router.post("/transactions/{transaction_id}/post", response_model=CashTransactionPublic)
async def post_cash_transaction(
    transaction_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    return await treasury_cash_service.post_cash_transaction(
        session,
        tenant_id,
        transaction_id,
        actor_id=actor_id,
    )


@router.post("/transactions/{transaction_id}/reverse", response_model=CashTransactionPublic)
async def reverse_cash_transaction(
    transaction_id: UUID,
    payload: CashTransactionReverseRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
):
    actor_id = getattr(request.state, "user_id", None)
    return await treasury_cash_service.reverse_cash_transaction(
        session,
        tenant_id,
        transaction_id,
        reason=payload.reason,
        actor_id=actor_id,
    )


__all__ = ["router"]
