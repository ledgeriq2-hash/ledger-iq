from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AiRun(BaseModel):
    __tablename__ = "ai_runs"

    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="SUCCESS")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    prediction_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("data_snapshots.id", ondelete="RESTRICT"),
        nullable=True,
    )
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    trigger: Mapped[str | None] = mapped_column(String(50), nullable=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_ai_runs_tenant_id", "tenant_id"),
        Index("ix_ai_runs_created_at", "created_at"),
        Index("ix_ai_runs_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_ai_runs_tenant_prediction_model_created_at", "tenant_id", "prediction_type", "model_version", "created_at"),
        Index("ix_ai_runs_status", "status"),
        Index("ix_ai_runs_prediction_type", "prediction_type"),
        Index("ix_ai_runs_model_version", "model_version"),
        Index("ix_ai_runs_data_snapshot_id", "data_snapshot_id"),
        Index("ix_ai_runs_requested_by", "requested_by"),
    )


__all__ = ["AiRun"]
