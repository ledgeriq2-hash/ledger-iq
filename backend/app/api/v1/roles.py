from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ADMIN, OWNER, require_roles
from app.models.user import User
from app.schemas.role import RoleCreate, RolePublic, RoleUpdate
from app.services import role_service

router = APIRouter(
    prefix="/roles",
    dependencies=[Depends(require_roles([OWNER, ADMIN]))],
)


@router.get("/", response_model=list[RolePublic])
async def list_roles(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID | None = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    roles = await role_service.list_roles(session, tenant_id)
    return roles


@router.get("/{role_id}", response_model=RolePublic)
async def get_role(
    role_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID | None = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    role = await role_service.get_role(session, tenant_id, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.post("/", response_model=RolePublic, status_code=status.HTTP_201_CREATED)
async def create_role(
    payload: RoleCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID | None = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    return await role_service.create_role(session, tenant_id, payload)


@router.put("/{role_id}", response_model=RolePublic)
async def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID | None = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    role = await role_service.update_role(session, tenant_id, role_id, payload)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID | None = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    deleted = await role_service.delete_role(session, tenant_id, role_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return None


__all__ = ["router"]
