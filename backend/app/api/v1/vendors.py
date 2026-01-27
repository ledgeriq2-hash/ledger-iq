from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import MAX_PAGE_SIZE, PaginationParams, pagination_params
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.purchase_invoice import (
    PurchaseBillCreateDraft,
    PurchaseBillListOut,
    PurchaseBillRead,
    PurchaseInvoiceStatus,
)
from app.schemas.vendor_payment import (
    VendorPaymentCreateDraft,
    VendorPaymentListOut,
    VendorPaymentRead,
    VendorPaymentStatus,
)
from app.schemas.vendor import (
    VendorCreate,
    VendorListOut,
    VendorOut,
    VendorStatus,
    VendorStatusUpdate,
    VendorUpdate,
)
from app.services import purchase_invoice_service, vendor_payment_service, vendor_service

router = APIRouter(prefix="/vendors")


def _resolve_pagination(
    base: PaginationParams,
    limit: int | None,
    offset: int | None,
) -> PaginationParams:
    if limit is None and offset is None:
        return base
    page_size = limit or base.page_size
    page = ((offset or 0) // page_size) + 1
    return PaginationParams(page=page, page_size=page_size)


@router.get("/", response_model=VendorListOut)
async def list_vendors(
    search: str | None = Query(default=None),
    status_filter: VendorStatus | None = Query(default=None, alias="status"),
    limit: int | None = Query(default=None, ge=1, le=MAX_PAGE_SIZE),
    offset: int | None = Query(default=None, ge=0),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    params = _resolve_pagination(pagination, limit, offset)
    vendors, total = await vendor_service.list_vendors(
        session,
        tenant_id,
        params,
        search=search,
        status=status_filter,
    )
    return VendorListOut.from_results(items=vendors, total=total, params=params)


@router.get("/{vendor_id}", response_model=VendorOut)
async def get_vendor(
    vendor_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    vendor = await vendor_service.get_vendor(session, tenant_id, vendor_id)
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


@router.post("/", response_model=VendorOut, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    payload: VendorCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await vendor_service.create_vendor(session, tenant_id, payload, actor_id=actor_id)


@router.patch("/{vendor_id}", response_model=VendorOut)
async def update_vendor(
    vendor_id: UUID,
    payload: VendorUpdate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    vendor = await vendor_service.update_vendor(session, tenant_id, vendor_id, payload, actor_id=actor_id)
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


@router.post("/{vendor_id}/status", response_model=VendorOut)
async def set_vendor_status(
    vendor_id: UUID,
    payload: VendorStatusUpdate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    status_value = VendorStatus.ACTIVE if payload.status == "active" else VendorStatus.INACTIVE
    vendor = await vendor_service.set_vendor_status(
        session,
        tenant_id,
        vendor_id,
        status=status_value,
        actor_id=actor_id,
    )
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


@router.get("/{vendor_id}/purchase-bills", response_model=PurchaseBillListOut)
async def list_vendor_purchase_bills(
    vendor_id: UUID,
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
    return PurchaseBillListOut.from_results(items=invoices, total=total, params=pagination)


@router.post("/{vendor_id}/purchase-bills", response_model=PurchaseBillRead, status_code=status.HTTP_201_CREATED)
async def create_vendor_purchase_bill(
    vendor_id: UUID,
    payload: PurchaseBillCreateDraft,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    data = payload.model_dump()
    data["vendor_id"] = vendor_id
    return await purchase_invoice_service.create_purchase_invoice(session, tenant_id, data)


@router.get("/{vendor_id}/payments", response_model=VendorPaymentListOut)
async def list_vendor_payments(
    vendor_id: UUID,
    status_filter: VendorPaymentStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    payments, total = await vendor_payment_service.list_payments(
        session,
        tenant_id,
        page=pagination.page,
        page_size=pagination.page_size,
        vendor_id=vendor_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
    )
    return VendorPaymentListOut.from_results(items=payments, total=total, params=pagination)


@router.post("/{vendor_id}/payments", response_model=VendorPaymentRead, status_code=status.HTTP_201_CREATED)
async def create_vendor_payment(
    vendor_id: UUID,
    payload: VendorPaymentCreateDraft,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    data = payload.model_dump()
    data["vendor_id"] = vendor_id
    return await vendor_payment_service.create_payment(session, tenant_id, data)


__all__ = ["router"]
