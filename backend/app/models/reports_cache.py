from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class ReportsCache(BaseModel):
    __tablename__ = "reports_cache"

    report_type: Mapped[str] = mapped_column(String(100), nullable=False)
    params_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_reports_cache_tenant_id", "tenant_id"),
        Index("ix_reports_cache_created_at", "created_at"),
        Index("ix_reports_cache_params_hash", "params_hash"),
    )


__all__ = ["ReportsCache"]
