from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import MAX_PAGE_SIZE, PaginationParams, pagination_params
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.vendor import VendorCreate, VendorListOut, VendorOut, VendorStatus, VendorUpdate
from app.services import vendor_service

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


__all__ = ["router"]
