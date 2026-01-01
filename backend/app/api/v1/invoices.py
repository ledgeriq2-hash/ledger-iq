from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.invoice import InvoiceCreate, InvoiceList, InvoicePaymentCreate, InvoicePublic, InvoiceUpdate
from app.services import billing_service, invoice_service

router = APIRouter(prefix="/invoices")


@router.get("/", response_model=InvoiceList)
async def list_invoices(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    invoices, total = await invoice_service.list_invoices(session, tenant_id, page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size if page_size else 0
    return InvoiceList(items=invoices, page=page, page_size=page_size, total=total, pages=pages)


@router.get("/{invoice_id}", response_model=InvoicePublic)
async def get_invoice(
    invoice_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    invoice = await invoice_service.get_invoice(session, tenant_id, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.post("/", response_model=InvoicePublic, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    await billing_service.enforce_plan_limit(session, tenant_id, "invoices")
    return await invoice_service.create_invoice(session, tenant_id, payload)


@router.post("/{invoice_id}/post", response_model=InvoicePublic)
async def post_invoice(
    invoice_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await invoice_service.post_invoice(session, tenant_id, invoice_id, actor_id=actor_id)


@router.post("/{invoice_id}/payments", response_model=InvoicePublic)
async def record_partial_payment(
    invoice_id: UUID,
    payload: InvoicePaymentCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await invoice_service.record_partial_payment(session, tenant_id, invoice_id, payload, actor_id=actor_id)


@router.put("/{invoice_id}", response_model=InvoicePublic)
async def update_invoice(
    invoice_id: UUID,
    payload: InvoiceUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    invoice = await invoice_service.update_invoice(session, tenant_id, invoice_id, payload)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    deleted = await invoice_service.delete_invoice(session, tenant_id, invoice_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return None


@router.post("/{invoice_id}/adjustments", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_invoice_adjustment(
    invoice_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    _ = session, tenant_id, invoice_id
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Invoice adjustments not implemented yet")


__all__ = ["router"]
