from __future__ import annotations

import uuid

from sqlalchemy import Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ErrorEvent(BaseModel):
    __tablename__ = "error_events"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    error_message: Mapped[str] = mapped_column(String(512), nullable=False)

    __table_args__ = (
        Index("ix_error_events_tenant_created", "tenant_id", "created_at"),
        Index("ix_error_events_created_at", "created_at"),
    )


__all__ = ["ErrorEvent"]
