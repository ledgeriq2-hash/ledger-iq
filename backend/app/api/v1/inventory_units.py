from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import PaginationParams, pagination_params
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.inventory_unit import (
    InventoryUnitCreate,
    InventoryUnitListOut,
    InventoryUnitOut,
)
from app.services import inventory_unit_service

router = APIRouter(prefix="/inventory-units")


@router.get("/", response_model=InventoryUnitListOut)
async def list_inventory_units(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    units, total = await inventory_unit_service.list_units(session, tenant_id, pagination)
    return InventoryUnitListOut.from_results(items=units, total=total, params=pagination)


@router.post("/", response_model=InventoryUnitOut, status_code=status.HTTP_201_CREATED)
async def create_inventory_unit(
    payload: InventoryUnitCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    return await inventory_unit_service.create_unit(session, tenant_id, payload)


__all__ = ["router"]
