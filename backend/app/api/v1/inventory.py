from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.stock_movement import MovementType, ReferenceType
from app.models.user import User
from app.schemas.stock_movement import (
    InventorySummaryResponse,
    StockMovementCreate,
    StockMovementList,
    StockMovementPublic,
    StockMovementUpdate,
)
from app.services import stock_movement_service

router = APIRouter(prefix="/inventory")


@router.get("/movements", response_model=StockMovementList)
async def list_movements(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    product_id: UUID | None = Query(None),
    movement_type: MovementType | None = Query(None),
    reference_type: ReferenceType | None = Query(None),
):
    items, total = await stock_movement_service.list_movements(
        session,
        tenant_id,
        page=page,
        page_size=page_size,
        product_id=product_id,
        movement_type=movement_type,
        reference_type=reference_type,
    )
    pages = (total + page_size - 1) // page_size if total else 0
    return StockMovementList(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.post("/movements", response_model=StockMovementPublic, status_code=status.HTTP_201_CREATED)
async def create_movement(
    payload: StockMovementCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    movement = await stock_movement_service.create_movement(session, tenant_id, payload)
    return movement


@router.get("/movements/{movement_id}", response_model=StockMovementPublic)
async def get_movement(
    movement_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    movement = await stock_movement_service.get_movement(session, tenant_id, movement_id)
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")
    return movement


@router.patch("/movements/{movement_id}", response_model=StockMovementPublic)
async def update_movement(
    movement_id: UUID,
    payload: StockMovementUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    movement = await stock_movement_service.update_movement(session, tenant_id, movement_id, payload)
    if not movement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")
    return movement


@router.delete("/movements/{movement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movement(
    movement_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    deleted = await stock_movement_service.delete_movement(session, tenant_id, movement_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movement not found")
    return None


@router.get("/summary", response_model=InventorySummaryResponse)
async def inventory_summary(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    items, total_value = await stock_movement_service.summarize_inventory(session, tenant_id)
    return InventorySummaryResponse(items=items, total_value=total_value)


@router.get("/valuation", response_model=InventorySummaryResponse)
async def inventory_valuation(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    items, total_value = await stock_movement_service.summarize_inventory(session, tenant_id)
    return InventorySummaryResponse(items=items, total_value=total_value)


__all__ = ["router"]
