from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.invoice import InvoicePublic
from app.schemas.recurring_invoice import (
    RecurringInvoiceCreate,
    RecurringInvoiceList,
    RecurringInvoicePublic,
    RecurringInvoiceUpdate,
)
from app.services import recurring_invoice_service

router = APIRouter(prefix="/recurring-invoices")


@router.get("/", response_model=RecurringInvoiceList)
async def list_recurring(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    frequency: str | None = Query(None),
):
    items, total = await recurring_invoice_service.list_recurring_invoices(
        session, tenant_id, page=page, page_size=page_size, frequency=frequency
    )
    public_items = [recurring_invoice_service.to_public_model(item) for item in items]
    pages = (total + page_size - 1) // page_size if total else 0
    return RecurringInvoiceList(items=public_items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("/", response_model=RecurringInvoicePublic, status_code=status.HTTP_201_CREATED)
async def create_recurring(
    payload: RecurringInvoiceCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    recurring = await recurring_invoice_service.create_recurring_invoice(session, tenant_id, payload)
    return recurring_invoice_service.to_public_model(recurring)


@router.get("/{recurring_id}", response_model=RecurringInvoicePublic)
async def get_recurring(
    recurring_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    recurring = await recurring_invoice_service.get_recurring_invoice(session, tenant_id, recurring_id)
    if not recurring:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring invoice not found")
    return recurring_invoice_service.to_public_model(recurring)


@router.patch("/{recurring_id}", response_model=RecurringInvoicePublic)
async def update_recurring(
    recurring_id: UUID,
    payload: RecurringInvoiceUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    recurring = await recurring_invoice_service.update_recurring_invoice(session, tenant_id, recurring_id, payload)
    if not recurring:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring invoice not found")
    return recurring_invoice_service.to_public_model(recurring)


@router.delete("/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring(
    recurring_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    deleted = await recurring_invoice_service.delete_recurring_invoice(session, tenant_id, recurring_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring invoice not found")
    return None


@router.post("/{recurring_id}/run", response_model=InvoicePublic)
async def run_now(
    recurring_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    invoice = await recurring_invoice_service.run_recurring_invoice(session, tenant_id, recurring_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring invoice not found")
    return invoice


__all__ = ["router"]
