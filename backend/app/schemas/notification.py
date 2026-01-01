from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import BaseSchema, IDTimestampMixin


class NotificationBase(BaseSchema):
    user_id: UUID | None = None
    type: str
    title: str
    message: str
    is_read: bool = False
    read_at: datetime | None = None


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseSchema):
    user_id: UUID | None = None
    type: str | None = None
    title: str | None = None
    message: str | None = None
    is_read: bool | None = None
    read_at: datetime | None = None


class NotificationPublic(IDTimestampMixin, NotificationBase):
    id: UUID


class NotificationList(BaseSchema):
    items: list[NotificationPublic]


__all__ = [
    "NotificationBase",
    "NotificationCreate",
    "NotificationUpdate",
    "NotificationPublic",
    "NotificationList",
]
