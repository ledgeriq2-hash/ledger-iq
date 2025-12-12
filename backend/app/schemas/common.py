from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BaseSchema(BaseModel):
    model_config = {"from_attributes": True}


class IDTimestampMixin(BaseSchema):
    id: UUID
    tenant_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


__all__ = ["BaseSchema", "IDTimestampMixin"]
