from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import PaginatedResponse, PaginationParams, paginate_query, pagination_params
from app.models.portal_token import PortalEntityType
from app.models.treasury_transaction import TreasuryTransaction
from app.models.user import User
from app.schemas.common import BaseSchema
from app.schemas.portal import (
    PortalBalanceResponse,
    PortalInvoicesResponse,
    PortalLinkRequest,
    PortalLinkResponse,
    PortalPaymentsResponse,
    PortalStatementResponse,
    PortalSummaryResponse,
)
from app.use_cases.portal.service import (
    generate_portal_link_use_case,
    portal_balance_response,
    portal_invoices_response,
    portal_payments_response,
    portal_statement_response,
    portal_summary_response,
    portal_rate_limit,
    validate_portal_token_or_error,
)

router = APIRouter(prefix="/portal")
contract_router = APIRouter(prefix="/portal")


def _d2(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))

class PortalContractSummaryStats(BaseSchema):
    transactions_total: int = 0
    incoming_total: Decimal = Decimal("0.00")
    outgoing_total: Decimal = Decimal("0.00")
    net_total: Decimal = Decimal("0.00")


class PortalContractSummaryResponse(BaseSchema):
    tenant_id: UUID
    currency: str = "USD"
    last_updated: str | None = None
    stats: PortalContractSummaryStats = Field(default_factory=PortalContractSummaryStats)


class PortalContractTransactionItem(BaseSchema):
    id: UUID
    treasury_id: UUID
    created_at: datetime
    amount: Decimal
    direction: str
    reference_type: str | None = None
    reference_id: UUID | None = None
    description: str


class PortalContractTransactionsResponse(PaginatedResponse[PortalContractTransactionItem]):
    currency: str = "USD"
    last_updated: str | None = None


@router.post("/link", response_model=PortalLinkResponse, status_code=status.HTTP_201_CREATED)
async def generate_portal_link(
    payload: PortalLinkRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    settings=Depends(deps.get_settings),
):
    await portal_rate_limit(request, settings, key="portal_link")
    result = await generate_portal_link_use_case(payload, request, session, tenant_id, settings)
    return PortalLinkResponse(**result)


@router.get("/{token}/summary", response_model=PortalSummaryResponse)
async def portal_summary(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    await portal_rate_limit(request, settings)
    _, _, portal_token = await validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.CUSTOMER
    )
    return await portal_summary_response(session, portal_token, settings)


@router.get("/{token}/balance", response_model=PortalBalanceResponse)
async def portal_balance(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
    as_of_date: date | None = Query(None),
):
    await portal_rate_limit(request, settings)
    _, _, portal_token = await validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.CUSTOMER
    )
    return await portal_balance_response(session, portal_token, as_of_date=as_of_date)


@router.get("/{token}/invoices", response_model=PortalInvoicesResponse)
async def portal_invoices(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
    pagination: PaginationParams = Depends(pagination_params),
) -> PortalInvoicesResponse:
    await portal_rate_limit(request, settings)
    _, _, portal_token = await validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.CUSTOMER
    )
    return await portal_invoices_response(session, portal_token, pagination)


@router.get("/{token}/payments", response_model=PortalPaymentsResponse)
async def portal_payments(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
    pagination: PaginationParams = Depends(pagination_params),
) -> PortalPaymentsResponse:
    await portal_rate_limit(request, settings)
    _, _, portal_token = await validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.CUSTOMER
    )
    return await portal_payments_response(session, portal_token, pagination)


@router.get("/{token}/statement", response_model=PortalStatementResponse)
async def portal_statement(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
):
    await portal_rate_limit(request, settings)
    _, _, portal_token = await validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.CUSTOMER
    )
    return await portal_statement_response(session, portal_token, from_date=from_date, to_date=to_date)


@contract_router.get("/summary", response_model=PortalContractSummaryResponse)
async def portal_contract_summary(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
) -> PortalContractSummaryResponse:
    """
    Contract portal summary for authenticated users.

    GET-only under `/api/portal/*` to keep portal contract read-only.
    """

    totals_stmt = select(
        func.count(TreasuryTransaction.id),
        func.coalesce(func.sum(case((TreasuryTransaction.direction == "in", TreasuryTransaction.amount), else_=0)), 0),
        func.coalesce(func.sum(case((TreasuryTransaction.direction == "out", TreasuryTransaction.amount), else_=0)), 0),
        func.coalesce(
            func.sum(
                case(
                    (TreasuryTransaction.direction == "in", TreasuryTransaction.amount),
                    else_=-TreasuryTransaction.amount,
                )
            ),
            0,
        ),
    ).where(TreasuryTransaction.tenant_id == tenant_id)
    result = await session.execute(totals_stmt)
    tx_count, incoming_total, outgoing_total, net_total = result.one()

    return PortalContractSummaryResponse(
        tenant_id=tenant_id,
        currency="USD",
        last_updated=None,
        stats=PortalContractSummaryStats(
            transactions_total=int(tx_count or 0),
            incoming_total=_d2(incoming_total),
            outgoing_total=_d2(outgoing_total),
            net_total=_d2(net_total),
        ),
    )


@contract_router.get("/transactions", response_model=PortalContractTransactionsResponse)
async def portal_contract_transactions(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    pagination: PaginationParams = Depends(pagination_params),
    direction: str | None = Query(default=None, description="Optional filter: in|out"),
) -> PortalContractTransactionsResponse:
    stmt = (
        select(TreasuryTransaction)
        .where(TreasuryTransaction.tenant_id == tenant_id)
        .order_by(TreasuryTransaction.created_at.desc())
    )
    if direction in {"in", "out"}:
        stmt = stmt.where(TreasuryTransaction.direction == direction)

    txs, total = await paginate_query(session, stmt, pagination)
    mapped: list[PortalContractTransactionItem] = []
    for tx in txs:
        mapped.append(
            PortalContractTransactionItem(
                id=tx.id,
                treasury_id=tx.treasury_id,
                created_at=tx.created_at,
                amount=_d2(tx.amount),
                direction=tx.direction,
                reference_type=tx.reference_type,
                reference_id=tx.reference_id,
                description=(f"{tx.reference_type}:{tx.reference_id}" if tx.reference_type else "Treasury transaction"),
            )
        )

    return PortalContractTransactionsResponse.from_results(items=mapped, total=total, params=pagination).model_copy(
        update={"currency": "USD", "last_updated": None}
    )


__all__ = ["router", "contract_router"]
