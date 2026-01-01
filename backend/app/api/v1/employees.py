from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.pagination import PaginatedResponse, PaginationParams, pagination_params
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeePublic, EmployeeUpdate
from app.services import employee_service

router = APIRouter(prefix="/employees")


@router.get("/", response_model=PaginatedResponse[EmployeePublic])
async def list_employees(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    pagination: PaginationParams = Depends(pagination_params),
):
    employees, total = await employee_service.list_employees(session, tenant_id, pagination)
    return PaginatedResponse[EmployeePublic].from_results(items=employees, total=total, params=pagination)


@router.get("/{employee_id}", response_model=EmployeePublic)
async def get_employee(
    employee_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    employee = await employee_service.get_employee(session, tenant_id, employee_id)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.post("/", response_model=EmployeePublic, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    return await employee_service.create_employee(session, tenant_id, payload)


@router.put("/{employee_id}", response_model=EmployeePublic)
async def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    employee = await employee_service.update_employee(session, tenant_id, employee_id, payload)
    if not employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    deleted = await employee_service.delete_employee(session, tenant_id, employee_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return None


__all__ = ["router"]
