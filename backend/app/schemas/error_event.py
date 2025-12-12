from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import BaseSchema


class ErrorEventPublic(BaseSchema):
    id: UUID
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    path: str
    method: str
    status_code: int
    error_message: str
    created_at: datetime


class ErrorEventsResponse(BaseSchema):
    items: list[ErrorEventPublic]


__all__ = ["ErrorEventPublic", "ErrorEventsResponse"]
