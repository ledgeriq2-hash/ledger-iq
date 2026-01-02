from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.customer import Customer
from app.models.employee import Employee
from app.models.invoice import Invoice, InvoiceStatus
from app.models.supplier import Supplier
from app.models.treasury_transaction import TreasuryTransaction
from app.schemas.common import BaseSchema

router = APIRouter(prefix="/dashboard")


class DashboardSummary(BaseSchema):
    customers: int
    suppliers: int
    employees: int
    open_invoices: int
    treasury_inflow: Decimal
    treasury_outflow: Decimal


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


__all__ = ["router"]
