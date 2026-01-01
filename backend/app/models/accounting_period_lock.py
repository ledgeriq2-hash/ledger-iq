from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class AccountingPeriodLock(BaseModel):
    __tablename__ = "accounting_period_locks"

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    locked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("(CURRENT_TIMESTAMP)"),
    )
    locked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        Index("ix_accounting_period_locks_tenant_id", "tenant_id"),
        Index("ix_accounting_period_locks_created_at", "created_at"),
        Index("ix_accounting_period_locks_tenant_start_end", "tenant_id", "start_date", "end_date"),
    )


__all__ = ["AccountingPeriodLock"]

