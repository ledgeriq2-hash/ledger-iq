from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ADMIN, OWNER, require_roles
from app.models.user import User
from app.schemas.user import UserCreate, UserList, UserPublic, UserUpdate
from app.services import billing_service, user_service
from app.utils.pagination import total_pages

router = APIRouter(prefix="/users")


@router.get("/", response_model=UserList)
async def list_users(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    users, total = await user_service.list_users(
        session, tenant_id, page=page, page_size=page_size, include_total=True
    )
    pages = total_pages(total, page_size)
    return UserList(items=users, page=page, page_size=page_size, total=total, pages=pages)


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    user = await user_service.get_user(session, tenant_id, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    await billing_service.enforce_plan_limit(session, tenant_id, "users")
    return await user_service.create_user(session, tenant_id, payload)


@router.put("/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    user = await user_service.update_user(session, tenant_id, user_id, payload)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    __: User = Depends(require_roles([OWNER, ADMIN])),
):
    deleted = await user_service.delete_user(session, tenant_id, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return None


__all__ = ["router"]
