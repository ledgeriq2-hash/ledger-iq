from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerList, CustomerPublic, CustomerUpdate
from app.services import customer_service

router = APIRouter(prefix="/customers")


@router.get("/", response_model=CustomerList)
async def list_customers(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    customers, total = await customer_service.list_customers(session, tenant_id, page=page, page_size=page_size)
    pages = (total + page_size - 1) // page_size if page_size else 0
    return CustomerList(items=customers, page=page, page_size=page_size, total=total, pages=pages)


@router.get("/{customer_id}", response_model=CustomerPublic)
async def get_customer(
    customer_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    customer = await customer_service.get_customer(session, tenant_id, customer_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.post("/", response_model=CustomerPublic, status_code=status.HTTP_201_CREATED)
async def create_customer(
    payload: CustomerCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    return await customer_service.create_customer(session, tenant_id, payload)


@router.put("/{customer_id}", response_model=CustomerPublic)
async def update_customer(
    customer_id: UUID,
    payload: CustomerUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    customer = await customer_service.update_customer(session, tenant_id, customer_id, payload)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: deps.User = Depends(deps.get_current_active_user),
):
    deleted = await customer_service.delete_customer(session, tenant_id, customer_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return None


__all__ = ["router"]
