from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import PaginationParams, pagination_params
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.unit_conversion import (
    UnitConversionCreate,
    UnitConversionListOut,
    UnitConversionOut,
    UnitConversionUpdate,
)
from app.services import unit_conversion_service

router = APIRouter(prefix="/unit-conversions")


@router.get("/", response_model=UnitConversionListOut)
async def list_unit_conversions(
    from_unit_id: UUID | None = Query(default=None),
    to_unit_id: UUID | None = Query(default=None),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    conversions, total = await unit_conversion_service.list_conversions(
        session,
        tenant_id,
        pagination,
        from_unit_id=from_unit_id,
        to_unit_id=to_unit_id,
    )
    return UnitConversionListOut.from_results(items=conversions, total=total, params=pagination)


@router.get("/{conversion_id}", response_model=UnitConversionOut)
async def get_unit_conversion(
    conversion_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    conversion = await unit_conversion_service.get_conversion(session, tenant_id, conversion_id)
    if not conversion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit conversion not found")
    return conversion


@router.post("/", response_model=UnitConversionOut, status_code=status.HTTP_201_CREATED)
async def create_unit_conversion(
    payload: UnitConversionCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    _ = request
    return await unit_conversion_service.create_conversion(session, tenant_id, payload)


@router.patch("/{conversion_id}", response_model=UnitConversionOut)
async def update_unit_conversion(
    conversion_id: UUID,
    payload: UnitConversionUpdate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    _ = request
    conversion = await unit_conversion_service.update_conversion(session, tenant_id, conversion_id, payload)
    if not conversion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit conversion not found")
    return conversion


@router.delete("/{conversion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit_conversion(
    conversion_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    _ = request
    deleted = await unit_conversion_service.delete_conversion(session, tenant_id, conversion_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit conversion not found")
    return None


__all__ = ["router"]
