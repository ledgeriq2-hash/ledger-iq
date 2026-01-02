from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AiInsight(BaseModel):
    __tablename__ = "ai_insights"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default="0")

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    reference_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("ix_ai_insights_tenant_id", "tenant_id"),
        Index("ix_ai_insights_created_at", "created_at"),
        Index("ix_ai_insights_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_ai_insights_type", "type"),
        Index("ix_ai_insights_severity", "severity"),
        Index("ix_ai_insights_confidence", "confidence"),
        Index("ix_ai_insights_reference", "reference_type", "reference_id"),
        Index("ix_ai_insights_run_id", "run_id"),
    )


__all__ = ["AiInsight"]

