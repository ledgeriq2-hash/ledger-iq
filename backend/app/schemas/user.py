from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import BaseSchema, IDTimestampMixin


class UserBase(BaseSchema):
    email: str
    full_name: str | None = None
    role_id: UUID | None = None
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseSchema):
    email: str | None = None
    full_name: str | None = None
    role_id: UUID | None = None
    password: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


class UserPublic(IDTimestampMixin, UserBase):
    last_login_at: datetime | None = None


__all__ = ["UserBase", "UserCreate", "UserUpdate", "UserPublic"]
