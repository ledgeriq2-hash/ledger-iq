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
from app.schemas.purchase_invoice import (
    PurchaseInvoiceCreate,
    PurchaseInvoiceListOut,
    PurchaseInvoiceOut,
    PurchaseInvoiceStatus,
    PurchaseInvoiceUpdate,
)
from app.services import purchase_invoice_service

router = APIRouter(prefix="/purchase-invoices")


@router.get("/", response_model=PurchaseInvoiceListOut)
async def list_purchase_invoices(
    vendor_id: UUID | None = Query(default=None),
    status_filter: PurchaseInvoiceStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    invoices, total = await purchase_invoice_service.list_purchase_invoices(
        session,
        tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        vendor_id=vendor_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
    )
    return PurchaseInvoiceListOut.from_results(items=invoices, total=total, params=pagination)


@router.get("/{invoice_id}", response_model=PurchaseInvoiceOut)
async def get_purchase_invoice(
    invoice_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    invoice = await purchase_invoice_service.get_purchase_invoice(session, tenant_id, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase invoice not found")
    return invoice


@router.post("/", response_model=PurchaseInvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_purchase_invoice(
    payload: PurchaseInvoiceCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await purchase_invoice_service.create_purchase_invoice(session, tenant_id, payload)


@router.patch("/{invoice_id}", response_model=PurchaseInvoiceOut)
async def update_purchase_invoice(
    invoice_id: UUID,
    payload: PurchaseInvoiceUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    invoice = await purchase_invoice_service.update_purchase_invoice(session, tenant_id, invoice_id, payload)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase invoice not found")
    return invoice


@router.post("/{invoice_id}/post", response_model=PurchaseInvoiceOut)
async def post_purchase_invoice(
    invoice_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await purchase_invoice_service.post_purchase_invoice(
        session,
        tenant_id,
        invoice_id,
        actor_id=actor_id,
    )


@router.post("/{invoice_id}/reverse", response_model=PurchaseInvoiceOut)
async def reverse_purchase_invoice(
    invoice_id: UUID,
    payload: JournalEntryReverseRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await purchase_invoice_service.reverse_purchase_invoice(
        session,
        tenant_id,
        invoice_id,
        reason=payload.reason,
        actor_id=actor_id,
    )


__all__ = ["router"]
