from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import PaginationParams, pagination_params
from app.models.user import User
from app.schemas.supplier import SupplierCreate, SupplierList, SupplierPublic, SupplierUpdate
from app.services import supplier_service

router = APIRouter(prefix="/suppliers")


@router.get("/", response_model=SupplierList)
async def list_suppliers(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    pagination: PaginationParams = Depends(pagination_params),
):
    suppliers, total = await supplier_service.list_suppliers(session, tenant_id, pagination)
    return SupplierList.from_results(items=suppliers, total=total, params=pagination)


@router.get("/{supplier_id}", response_model=SupplierPublic)
async def get_supplier(
    supplier_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    supplier = await supplier_service.get_supplier(session, tenant_id, supplier_id)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier


@router.post("/", response_model=SupplierPublic, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    payload: SupplierCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    return await supplier_service.create_supplier(session, tenant_id, payload)


@router.put("/{supplier_id}", response_model=SupplierPublic)
async def update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    supplier = await supplier_service.update_supplier(session, tenant_id, supplier_id, payload)
    if not supplier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return supplier


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    deleted = await supplier_service.delete_supplier(session, tenant_id, supplier_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")
    return None


__all__ = ["router"]
