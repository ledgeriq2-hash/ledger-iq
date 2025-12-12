from __future__ import annotations

import uuid

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ActivityLog(BaseModel):
    __tablename__ = "activity_logs"

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | uuid.UUID] = mapped_column(String(255), nullable=False)
    details_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        Index("ix_activity_logs_tenant_id", "tenant_id"),
        Index("ix_activity_logs_created_at", "created_at"),
    )


__all__ = ["ActivityLog"]
