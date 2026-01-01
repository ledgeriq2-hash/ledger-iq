from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import MAX_PAGE_SIZE, PaginationParams, pagination_params
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeePublic,
    EmployeeStatusFilter,
    EmployeeUpdate,
)
from app.services import employee_service

router = APIRouter(prefix="/employees")


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


@router.get("/", response_model=EmployeeListResponse)
async def list_employees(
    search: str | None = Query(default=None),
    status_filter: EmployeeStatusFilter | None = Query(default=None, alias="status"),
    include_deleted: bool = Query(default=False),
    limit: int | None = Query(default=None, ge=1, le=MAX_PAGE_SIZE),
    offset: int | None = Query(default=None, ge=0),
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
    pagination: PaginationParams = Depends(pagination_params),
):
    params = _resolve_pagination(pagination, limit, offset)
    employees, total = await employee_service.list_employees(
        session,
        tenant_id,
        params,
        search=search,
        status_filter=status_filter,
        include_deleted=include_deleted,
    )
    return EmployeeListResponse.from_results(items=employees, total=total, params=params)


@router.get("/{employee_id}", response_model=EmployeePublic)
async def get_employee(
    employee_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT, VIEWER])),
):
    employee = await employee_service.get_employee(session, tenant_id, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.post("/", response_model=EmployeePublic, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    return await employee_service.create_employee(session, tenant_id, payload, actor_id=actor_id)


@router.patch("/{employee_id}", response_model=EmployeePublic)
async def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    employee = await employee_service.update_employee(
        session,
        tenant_id,
        employee_id,
        payload,
        actor_id=actor_id,
    )
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.post("/{employee_id}/deactivate", response_model=EmployeePublic)
async def deactivate_employee(
    employee_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    employee = await employee_service.deactivate_employee(session, tenant_id, employee_id, actor_id=actor_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.post("/{employee_id}/reactivate", response_model=EmployeePublic)
async def reactivate_employee(
    employee_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    employee = await employee_service.reactivate_employee(session, tenant_id, employee_id, actor_id=actor_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN, ACCOUNTANT])),
):
    actor_id = getattr(request.state, "user_id", None)
    deleted = await employee_service.soft_delete_employee(session, tenant_id, employee_id, actor_id=actor_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return None


__all__ = ["router"]
