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
    PurchaseBillCreateDraft,
    PurchaseBillListOut,
    PurchaseBillLineRead,
    PurchaseBillRead,
    PurchaseBillUpdateDraft,
    PurchaseInvoiceLineCreate,
    PurchaseInvoiceLineUpdate,
    PurchaseInvoiceStatus,
)
from app.services import purchase_invoice_service

router = APIRouter(prefix="/purchase-bills")


@router.get("/", response_model=PurchaseBillListOut)
async def list_purchase_bills(
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
    bills, total = await purchase_invoice_service.list_purchase_invoices(
        session,
        tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        vendor_id=vendor_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
    )
    return PurchaseBillListOut.from_results(items=bills, total=total, params=pagination)


@router.get("/{bill_id}", response_model=PurchaseBillRead)
async def get_purchase_bill(
    bill_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    bill = await purchase_invoice_service.get_purchase_invoice(session, tenant_id, bill_id)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase bill not found")
    return bill


@router.get("/{bill_id}/lines", response_model=list[PurchaseBillLineRead])
async def list_purchase_bill_lines(
    bill_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    return await purchase_invoice_service.list_purchase_invoice_lines(session, tenant_id, bill_id)


@router.post("/{bill_id}/lines", response_model=PurchaseBillLineRead, status_code=status.HTTP_201_CREATED)
async def add_purchase_bill_line(
    bill_id: UUID,
    payload: PurchaseInvoiceLineCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await purchase_invoice_service.add_purchase_invoice_line(session, tenant_id, bill_id, payload)


@router.put("/{bill_id}/lines/{line_id}", response_model=PurchaseBillLineRead)
async def update_purchase_bill_line(
    bill_id: UUID,
    line_id: UUID,
    payload: PurchaseInvoiceLineUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await purchase_invoice_service.update_purchase_invoice_line(
        session, tenant_id, bill_id, line_id, payload
    )


@router.delete("/{bill_id}/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_bill_line(
    bill_id: UUID,
    line_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    deleted = await purchase_invoice_service.delete_purchase_invoice_line(session, tenant_id, bill_id, line_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase bill line not found")
    return None


@router.post("/", response_model=PurchaseBillRead, status_code=status.HTTP_201_CREATED)
async def create_purchase_bill(
    payload: PurchaseBillCreateDraft,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await purchase_invoice_service.create_purchase_invoice(session, tenant_id, payload)


@router.put("/{bill_id}", response_model=PurchaseBillRead)
async def update_purchase_bill(
    bill_id: UUID,
    payload: PurchaseBillUpdateDraft,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    bill = await purchase_invoice_service.update_purchase_invoice(session, tenant_id, bill_id, payload)
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase bill not found")
    return bill


@router.post("/{bill_id}/post", response_model=PurchaseBillRead)
async def post_purchase_bill(
    bill_id: UUID,
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
        bill_id,
        actor_id=actor_id,
    )


@router.post("/{bill_id}/reverse", response_model=PurchaseBillRead)
async def reverse_purchase_bill(
    bill_id: UUID,
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
        bill_id,
        reason=payload.reason,
        actor_id=actor_id,
    )


__all__ = ["router"]
