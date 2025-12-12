from __future__ import annotations

import uuid

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Attachment(BaseModel):
    __tablename__ = "attachments"

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size: Mapped[int | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_attachments_tenant_id", "tenant_id"),
        Index("ix_attachments_created_at", "created_at"),
        Index("ix_attachments_entity", "entity_type", "entity_id"),
    )


__all__ = ["Attachment"]
