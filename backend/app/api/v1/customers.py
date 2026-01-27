from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import MAX_PAGE_SIZE, PaginationParams, pagination_params
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.models.customer import CustomerStatus
from app.schemas.customer import (
    CustomerCreate,
    CustomerListOut,
    CustomerOut,
    CustomerStatusFilter,
    CustomerStatusUpdate,
    CustomerUpdate,
)
from app.schemas.sales_invoice import SalesInvoiceCreateDraft, SalesInvoiceListOut, SalesInvoiceRead, SalesInvoiceStatus
from app.services import sales_invoice_service
from app.services import customer_service

router = APIRouter(prefix="/customers")


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


@router.get("/", response_model=CustomerListOut)
async def list_customers(
    search: str | None = Query(default=None),
    status_filter: CustomerStatusFilter | None = Query(default=None, alias="status"),
    limit: int | None = Query(default=None, ge=1, le=MAX_PAGE_SIZE),
    offset: int | None = Query(default=None, ge=0),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    params = _resolve_pagination(pagination, limit, offset)
    customers, total = await customer_service.list_customers(
        session,
        tenant_id,
        params,
        search=search,
        status_filter=status_filter,
    )
    return CustomerListOut.from_results(items=customers, total=total, params=params)


@router.get("/{customer_id}", response_model=CustomerOut)
async def get_customer(
    customer_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    customer = await customer_service.get_customer(session, tenant_id, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.post("/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await customer_service.create_customer(session, tenant_id, payload, actor_id=actor_id)


@router.patch("/{customer_id}", response_model=CustomerOut)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    customer = await customer_service.update_customer(session, tenant_id, customer_id, payload, actor_id=actor_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.post("/{customer_id}/deactivate", response_model=CustomerOut)
async def deactivate_customer(
    customer_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    customer = await customer_service.deactivate_customer(session, tenant_id, customer_id, actor_id=actor_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.post("/{customer_id}/reactivate", response_model=CustomerOut)
async def reactivate_customer(
    customer_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    customer = await customer_service.reactivate_customer(session, tenant_id, customer_id, actor_id=actor_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.post("/{customer_id}/status", response_model=CustomerOut)
async def set_customer_status(
    customer_id: UUID,
    payload: CustomerStatusUpdate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    status_value = CustomerStatus.ACTIVE if payload.status == "active" else CustomerStatus.INACTIVE
    customer = await customer_service.set_customer_status(
        session,
        tenant_id,
        customer_id,
        status=status_value,
        actor_id=actor_id,
    )
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    deleted = await customer_service.delete_customer(session, tenant_id, customer_id, actor_id=actor_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return None


@router.get("/{customer_id}/sales-invoices", response_model=SalesInvoiceListOut)
async def list_customer_sales_invoices(
    customer_id: UUID,
    status_filter: SalesInvoiceStatus | None = Query(default=None, alias="status"),
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
        date_from=None,
        date_to=None,
    )
    return SalesInvoiceListOut.from_results(items=invoices, total=total, params=pagination)


@router.post("/{customer_id}/sales-invoices", response_model=SalesInvoiceRead, status_code=status.HTTP_201_CREATED)
async def create_customer_sales_invoice(
    customer_id: UUID,
    payload: SalesInvoiceCreateDraft,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    data = payload.model_dump()
    data["customer_id"] = customer_id
    return await sales_invoice_service.create_sales_invoice(session, tenant_id, data)


__all__ = ["router"]
