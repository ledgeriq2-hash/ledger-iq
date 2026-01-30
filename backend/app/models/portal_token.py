from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, text
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
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_portal_tokens_tenant_id", "tenant_id"),
        Index("ix_portal_tokens_created_at", "created_at"),
        Index("ix_portal_tokens_entity", "entity_type", "entity_id"),
        Index("ix_portal_tokens_tenant_entity_created", "tenant_id", "entity_type", "entity_id", "created_at"),
        Index("ix_portal_tokens_tenant_entity_expires", "tenant_id", "entity_type", "entity_id", "expires_at"),
        Index("ix_portal_tokens_token_hash", "token_hash", unique=True),
        UniqueConstraint("tenant_id", "entity_type", "entity_id", "token_hash", name="uq_portal_tokens_tenant_entity_token"),
    )


__all__ = ["PortalToken", "PortalEntityType"]
