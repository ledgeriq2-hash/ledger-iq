from __future__ import annotations

from datetime import datetime
import uuid
from enum import Enum

from sqlalchemy import Boolean, DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class PortalEntityType(str, Enum):
    CUSTOMER = "CUSTOMER"
    SUPPLIER = "SUPPLIER"


class PortalToken(BaseModel):
    __tablename__ = "portal_tokens"

    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[PortalEntityType] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))

    __table_args__ = (
        Index("ix_portal_tokens_tenant_id", "tenant_id"),
        Index("ix_portal_tokens_created_at", "created_at"),
        Index("ix_portal_tokens_entity", "entity_type", "entity_id"),
    )


__all__ = ["PortalToken", "PortalEntityType"]
