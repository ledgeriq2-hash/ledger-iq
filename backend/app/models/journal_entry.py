from __future__ import annotations

from datetime import date
import uuid

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class JournalEntry(BaseModel):
    __tablename__ = "journal_entries"

    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_posted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fx_rate: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    source_module: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reversed_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )

    lines: Mapped[list["JournalEntryLine"]] = relationship(
        "JournalEntryLine",
        back_populates="journal_entry",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_journal_entries_tenant_id", "tenant_id"),
        Index("ix_journal_entries_created_at", "created_at"),
        Index("ix_journal_entries_date", "date"),
        Index("ix_journal_entries_source_module", "source_module"),
    )


__all__ = ["JournalEntry"]
