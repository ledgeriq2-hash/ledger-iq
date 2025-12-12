from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema


class FeedbackCreate(BaseSchema):
    category: str = Field(..., pattern="^(bug|idea|confusion|other)$")
    message: str


class FeedbackPublic(BaseSchema):
    id: UUID
    tenant_id: UUID | None = None
    user_id: UUID | None = None
    category: str
    message: str
    created_at: datetime


class FeedbackListResponse(BaseSchema):
    items: list[FeedbackPublic]


__all__ = ["FeedbackCreate", "FeedbackPublic", "FeedbackListResponse"]
