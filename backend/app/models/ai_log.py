from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AiLog(BaseModel):
    __tablename__ = "ai_logs"

    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    output_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)

    __table_args__ = (
        Index("ix_ai_logs_tenant_id", "tenant_id"),
        Index("ix_ai_logs_created_at", "created_at"),
        Index("ix_ai_logs_model_type", "model_type"),
    )


__all__ = ["AiLog"]
