from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import PaginationParams, pagination_params
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.journals import JournalEntryReverseRequest
from app.schemas.sales_invoice import (
    SalesInvoiceCreate,
    SalesInvoiceLineCreate,
    SalesInvoiceLineRead,
    SalesInvoiceLineUpdate,
    SalesInvoiceListOut,
    SalesInvoiceOut,
    SalesInvoiceRead,
    SalesInvoiceStatus,
    SalesInvoiceUpdate,
    SalesInvoiceUpdateDraft,
)
from app.services import sales_invoice_service

router = APIRouter(prefix="/sales-invoices")


@router.get("/", response_model=SalesInvoiceListOut)
async def list_sales_invoices(
    customer_id: UUID | None = Query(default=None),
    status_filter: SalesInvoiceStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    invoices, total = await sales_invoice_service.list_sales_invoices(
        session,
        tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        customer_id=customer_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
    )
    return SalesInvoiceListOut.from_results(items=invoices, total=total, params=pagination)


@router.get("/{invoice_id}", response_model=SalesInvoiceOut)
async def get_sales_invoice(
    invoice_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    invoice = await sales_invoice_service.get_sales_invoice(session, tenant_id, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales invoice not found")
    return invoice


@router.get("/{invoice_id}/lines", response_model=list[SalesInvoiceLineRead])
async def list_sales_invoice_lines(
    invoice_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    return await sales_invoice_service.list_sales_invoice_lines(session, tenant_id, invoice_id)


@router.post("/{invoice_id}/lines", response_model=SalesInvoiceLineRead, status_code=status.HTTP_201_CREATED)
async def add_sales_invoice_line(
    invoice_id: UUID,
    payload: SalesInvoiceLineCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await sales_invoice_service.add_sales_invoice_line(session, tenant_id, invoice_id, payload)


@router.put("/{invoice_id}/lines/{line_id}", response_model=SalesInvoiceLineRead)
async def update_sales_invoice_line(
    invoice_id: UUID,
    line_id: UUID,
    payload: SalesInvoiceLineUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await sales_invoice_service.update_sales_invoice_line(
        session, tenant_id, invoice_id, line_id, payload
    )


@router.delete("/{invoice_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sales_invoice_line(
    invoice_id: UUID,
    line_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    deleted = await sales_invoice_service.delete_sales_invoice_line(session, tenant_id, invoice_id, line_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales invoice line not found")
    return None


@router.post("/", response_model=SalesInvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_sales_invoice(
    payload: SalesInvoiceCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await sales_invoice_service.create_sales_invoice(session, tenant_id, payload)


@router.patch("/{invoice_id}", response_model=SalesInvoiceOut)
async def update_sales_invoice(
    invoice_id: UUID,
    payload: SalesInvoiceUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    invoice = await sales_invoice_service.update_sales_invoice(session, tenant_id, invoice_id, payload)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales invoice not found")
    return invoice


@router.put("/{invoice_id}", response_model=SalesInvoiceRead)
async def update_sales_invoice_draft(
    invoice_id: UUID,
    payload: SalesInvoiceUpdateDraft,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    invoice = await sales_invoice_service.update_sales_invoice(session, tenant_id, invoice_id, payload)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sales invoice not found")
    return invoice


@router.post("/{invoice_id}/post", response_model=SalesInvoiceOut)
async def post_sales_invoice(
    invoice_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await sales_invoice_service.post_sales_invoice(session, tenant_id, invoice_id, actor_id=actor_id)


@router.post("/{invoice_id}/reverse", response_model=SalesInvoiceOut)
async def reverse_sales_invoice(
    invoice_id: UUID,
    payload: JournalEntryReverseRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await sales_invoice_service.reverse_sales_invoice(
        session,
        tenant_id,
        invoice_id,
        reason=payload.reason,
        actor_id=actor_id,
    )


__all__ = ["router"]
