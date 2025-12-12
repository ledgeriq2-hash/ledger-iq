from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ADMIN, OWNER, require_roles
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantPublic, TenantUpdate
from app.services import tenant_service

router = APIRouter(prefix="/tenants")


@router.get("/", response_model=list[TenantPublic])
async def list_tenants(
    session: AsyncSession = Depends(deps.get_db),
    tenant_scope: UUID | None = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    return await tenant_service.list_tenants(session, tenant_scope)


@router.get("/{tenant_id}", response_model=TenantPublic)
async def get_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_scope: UUID | None = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    tenant = await tenant_service.get_tenant(session, tenant_id, tenant_scope)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.post("/", response_model=TenantPublic, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_scope: UUID | None = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    return await tenant_service.create_tenant(session, payload, scope_id=tenant_scope)


@router.put("/{tenant_id}", response_model=TenantPublic)
async def update_tenant(
    tenant_id: UUID,
    payload: TenantUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_scope: UUID | None = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    tenant = await tenant_service.update_tenant(session, tenant_id, payload, scope_id=tenant_scope)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_scope: UUID | None = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    deleted = await tenant_service.delete_tenant(session, tenant_id, scope_id=tenant_scope)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return None


@router.post("/initialize", response_model=dict)
async def initialize_tenant(
    payload: dict,
    session: AsyncSession = Depends(deps.get_db),
    tenant_scope: UUID | None = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    tenant_payload = payload.get("tenant")
    admin_payload = payload.get("admin_user")
    roles_payload = payload.get("roles") or []
    if not tenant_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant payload required")
    return await tenant_service.initialize_tenant(session, tenant_payload, admin_payload, roles_payload)


__all__ = ["router"]
