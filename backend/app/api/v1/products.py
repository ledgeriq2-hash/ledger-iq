from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.product import ProductCreate, ProductList, ProductPublic, ProductUpdate
from app.services import product_service

router = APIRouter(prefix="/products")


@router.get("/", response_model=ProductList)
async def list_products(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    products = await product_service.list_products(session, tenant_id)
    return ProductList(items=products)


@router.get("/{product_id}", response_model=ProductPublic)
async def get_product(
    product_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    product = await product_service.get_product(session, tenant_id, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.post("/", response_model=ProductPublic, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    return await product_service.create_product(session, tenant_id, payload)


@router.put("/{product_id}", response_model=ProductPublic)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    product = await product_service.update_product(session, tenant_id, product_id, payload)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    deleted = await product_service.delete_product(session, tenant_id, product_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return None


__all__ = ["router"]
