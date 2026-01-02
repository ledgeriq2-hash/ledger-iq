from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import PaginationParams, paginate_query, pagination_params
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.customer import Customer
from app.models.employee import Employee
from app.models.expense import Expense
from app.models.invoice import Invoice, InvoiceStatus
from app.models.supplier import Supplier
from app.models.treasury_transaction import TreasuryTransaction
from app.schemas.common import BaseSchema
from app.services import settings_service

router = APIRouter(prefix="/dashboard")


class DashboardSummary(BaseSchema):
    customers: int
    suppliers: int
    employees: int
    open_invoices: int
    treasury_inflow: Decimal
    treasury_outflow: Decimal


class DashboardKpis(BaseSchema):
    revenue: Decimal | None = None
    expenses: Decimal | None = None
    profit: Decimal | None = None
    net_cash: Decimal | None = None


class DashboardMetricsResponse(BaseSchema):
    currency: str
    last_updated: datetime
    kpis: DashboardKpis
    charts: dict | None = None


class DashboardRecentTransaction(BaseSchema):
    id: UUID
    description: str | None = None
    reference_type: str | None = None
    direction: str
    amount: Decimal
    created_at: datetime


class DashboardRecentTransactionsResponse(BaseSchema):
    items: list[DashboardRecentTransaction]
    page: int
    page_size: int
    total: int
    pages: int
    currency: str


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    customers = await session.scalar(
        select(func.count()).select_from(Customer).where(Customer.tenant_id == tenant_id)
    )
    suppliers = await session.scalar(
        select(func.count()).select_from(Supplier).where(Supplier.tenant_id == tenant_id)
    )
    employees = await session.scalar(
        select(func.count()).select_from(Employee).where(Employee.tenant_id == tenant_id)
    )
    open_invoices = await session.scalar(
        select(func.count()).select_from(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_([InvoiceStatus.POSTED, InvoiceStatus.PARTIAL, InvoiceStatus.OVERDUE]),
        )
    )
    inflow = await session.scalar(
        select(func.coalesce(func.sum(TreasuryTransaction.amount), 0)).where(
            TreasuryTransaction.tenant_id == tenant_id,
            TreasuryTransaction.direction == "in",
        )
    )
    outflow = await session.scalar(
        select(func.coalesce(func.sum(TreasuryTransaction.amount), 0)).where(
            TreasuryTransaction.tenant_id == tenant_id,
            TreasuryTransaction.direction == "out",
        )
    )
    return DashboardSummary(
        customers=int(customers or 0),
        suppliers=int(suppliers or 0),
        employees=int(employees or 0),
        open_invoices=int(open_invoices or 0),
        treasury_inflow=Decimal(str(inflow or 0)).quantize(Decimal("0.01")),
        treasury_outflow=Decimal(str(outflow or 0)).quantize(Decimal("0.01")),
    )


@router.get("/metrics", response_model=DashboardMetricsResponse)
async def dashboard_metrics(
    months: int = Query(12, ge=1, le=36),
    time_basis: str = Query("event_date"),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    _ = months, time_basis
    settings = await settings_service.get_settings(session, tenant_id)
    currency = settings.currency or "USD"

    revenue = await session.scalar(
        select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status.in_(
                [InvoiceStatus.POSTED, InvoiceStatus.PARTIAL, InvoiceStatus.PAID, InvoiceStatus.OVERDUE]
            ),
        )
    )
    expenses = await session.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.tenant_id == tenant_id)
    )
    inflow = await session.scalar(
        select(func.coalesce(func.sum(TreasuryTransaction.amount), 0)).where(
            TreasuryTransaction.tenant_id == tenant_id,
            TreasuryTransaction.direction == "in",
        )
    )
    outflow = await session.scalar(
        select(func.coalesce(func.sum(TreasuryTransaction.amount), 0)).where(
            TreasuryTransaction.tenant_id == tenant_id,
            TreasuryTransaction.direction == "out",
        )
    )

    revenue_value = Decimal(str(revenue or 0)).quantize(Decimal("0.01"))
    expense_value = Decimal(str(expenses or 0)).quantize(Decimal("0.01"))
    inflow_value = Decimal(str(inflow or 0)).quantize(Decimal("0.01"))
    outflow_value = Decimal(str(outflow or 0)).quantize(Decimal("0.01"))

    kpis = DashboardKpis(
        revenue=revenue_value,
        expenses=expense_value,
        profit=(revenue_value - expense_value),
        net_cash=(inflow_value - outflow_value),
    )
    return DashboardMetricsResponse(
        currency=currency,
        last_updated=datetime.now(timezone.utc),
        kpis=kpis,
        charts={"revenue_by_month": []},
    )


def _format_description(transaction: TreasuryTransaction) -> str | None:
    base = transaction.reference_type or transaction.movement_type or None
    if not base:
        return None
    return str(base).replace("_", " ").title()


@router.get("/recent-transactions", response_model=DashboardRecentTransactionsResponse)
async def dashboard_recent_transactions(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    settings = await settings_service.get_settings(session, tenant_id)
    currency = settings.currency or "USD"
    statement = (
        select(TreasuryTransaction)
        .where(TreasuryTransaction.tenant_id == tenant_id)
        .order_by(TreasuryTransaction.created_at.desc())
    )
    items, total = await paginate_query(session, statement, pagination)
    mapped = [
        DashboardRecentTransaction(
            id=transaction.id,
            description=_format_description(transaction),
            reference_type=transaction.reference_type,
            direction=transaction.direction,
            amount=transaction.amount,
            created_at=transaction.created_at,
        )
        for transaction in items
    ]
    pages = ceil(total / pagination.page_size) if pagination.page_size else 0
    return DashboardRecentTransactionsResponse(
        items=mapped,
        page=pagination.page,
        page_size=pagination.page_size,
        total=total,
        pages=pages,
        currency=currency,
    )


__all__ = ["router"]
