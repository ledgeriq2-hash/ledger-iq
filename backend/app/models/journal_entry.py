from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.journal_entry_line import JournalEntryLine


class JournalEntry(BaseModel):
    __tablename__ = "journal_entries"

    date: Mapped[date] = mapped_column(Date, nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=text("CURRENT_DATE"))
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
    adjustment_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    adjusted_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    treasury_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treasury_transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_reversed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    is_voided: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    voided_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    lines: Mapped[list[JournalEntryLine]] = relationship(
        "JournalEntryLine",
        back_populates="journal_entry",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_journal_entries_tenant_id", "tenant_id"),
        Index("ix_journal_entries_created_at", "created_at"),
        Index("ix_journal_entries_date", "date"),
        Index("ix_journal_entries_event_date", "event_date"),
        Index("ix_journal_entries_source_module", "source_module"),
        Index("ix_journal_entries_idempotency_key", "idempotency_key"),
        Index("ix_journal_entries_treasury_transaction_id", "treasury_transaction_id"),
    )


__all__ = ["JournalEntry"]
