from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.fx_revaluation_run import FXRevaluationRun


class FXRevaluationLine(BaseModel):
    __tablename__ = "fx_revaluation_lines"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fx_revaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    foreign_remaining: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    old_base_remaining: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    new_base_remaining: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    delta_base: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))

    run: Mapped["FXRevaluationRun"] = relationship("FXRevaluationRun", back_populates="lines", lazy="joined")

    __table_args__ = (
        Index("ix_fx_revaluation_lines_tenant_id", "tenant_id"),
        Index("ix_fx_revaluation_lines_created_at", "created_at"),
        Index("ix_fx_revaluation_lines_run_id", "run_id"),
        Index("ix_fx_revaluation_lines_source", "source_type", "source_id"),
    )


__all__ = ["FXRevaluationLine"]
