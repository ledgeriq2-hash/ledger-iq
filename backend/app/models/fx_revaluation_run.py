from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.fx_revaluation_line import FXRevaluationLine


class FXRevaluationStatus(str, Enum):
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class FXRevaluationRun(BaseModel):
    __tablename__ = "fx_revaluation_runs"

    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(10), nullable=False)
    reval_fx_rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    status: Mapped[FXRevaluationStatus] = mapped_column(
        SqlEnum(FXRevaluationStatus, name="fx_revaluation_status"),
        nullable=False,
        server_default=FXRevaluationStatus.POSTED.value,
    )
    posting_journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list["FXRevaluationLine"]] = relationship(
        "FXRevaluationLine",
        back_populates="run",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "period_year",
            "period_month",
            "currency_code",
            name="uq_fx_revaluation_runs_tenant_period_currency",
        ),
        Index("ix_fx_revaluation_runs_tenant_id", "tenant_id"),
        Index("ix_fx_revaluation_runs_created_at", "created_at"),
        Index("ix_fx_revaluation_runs_period", "period_year", "period_month"),
        Index("ix_fx_revaluation_runs_currency", "currency_code"),
    )


__all__ = ["FXRevaluationRun", "FXRevaluationStatus"]
