from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationList,
    NotificationPublic,
    NotificationUpdate,
)
from app.services import notification_service

router = APIRouter(prefix="/notifications")


@router.get("/", response_model=NotificationList)
async def list_notifications(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    notifications = await notification_service.list_notifications(session, tenant_id)
    return NotificationList(items=notifications)


@router.get("/{notification_id}", response_model=NotificationPublic)
async def get_notification(
    notification_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    notification = await notification_service.get_notification(session, tenant_id, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.post("/", response_model=NotificationPublic, status_code=status.HTTP_201_CREATED)
async def create_notification(
    payload: NotificationCreate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    return await notification_service.create_notification(session, tenant_id, payload)


@router.put("/{notification_id}", response_model=NotificationPublic)
async def update_notification(
    notification_id: UUID,
    payload: NotificationUpdate,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    notification = await notification_service.update_notification(session, tenant_id, notification_id, payload)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.post("/{notification_id}/read", response_model=NotificationPublic)
async def mark_read(
    notification_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    notification = await notification_service.mark_notification_read(session, tenant_id, notification_id, True)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    deleted = await notification_service.delete_notification(session, tenant_id, notification_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return None


__all__ = ["router"]
