from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.dimension_value import DimensionValue
    from app.models.journal_line import JournalLine


class JournalLineDimension(BaseModel):
    __tablename__ = "journal_line_dimensions"

    journal_line_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_lines.id", ondelete="CASCADE"),
        nullable=False,
    )
    dimension_value_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dimension_values.id", ondelete="RESTRICT"),
        nullable=False,
    )

    journal_line: Mapped["JournalLine"] = relationship("JournalLine", lazy="joined")
    dimension_value: Mapped["DimensionValue"] = relationship("DimensionValue", lazy="joined")

    __table_args__ = (
        UniqueConstraint(
            "journal_line_id",
            "dimension_value_id",
            name="uq_journal_line_dimension_value",
        ),
        Index("ix_journal_line_dimensions_tenant_id", "tenant_id"),
        Index("ix_journal_line_dimensions_created_at", "created_at"),
        Index("ix_journal_line_dimensions_journal_line_id", "journal_line_id"),
        Index("ix_journal_line_dimensions_dimension_value_id", "dimension_value_id"),
    )


__all__ = ["JournalLineDimension"]
