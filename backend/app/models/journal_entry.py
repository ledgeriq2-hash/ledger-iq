from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.journal_entry_line import JournalEntryLine
    from app.models.journal_line import JournalLine


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
    entry_no: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("uuid_generate_v4()"),
    )
    entry_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE"),
    )
    posting_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("EXTRACT(YEAR FROM CURRENT_DATE)::int"),
    )
    period_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("EXTRACT(MONTH FROM CURRENT_DATE)::int"),
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'Posted'"),
    )
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'legacy'"),
    )
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        server_default=text("'USD'"),
    )
    total_debit_base: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
    )
    total_credit_base: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
    )
    reversal_of_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list[JournalEntryLine]] = relationship(
        "JournalEntryLine",
        back_populates="journal_entry",
        lazy="selectin",
    )
    ledger_lines: Mapped[list[JournalLine]] = relationship(
        "JournalLine",
        back_populates="entry",
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
        Index("ix_journal_entries_entry_no", "entry_no", unique=True),
        Index("ix_journal_entries_entry_date", "entry_date"),
        Index("ix_journal_entries_period_year_month", "period_year", "period_month"),
        Index("ix_journal_entries_source_type_id", "source_type", "source_id"),
        Index(
            "ux_journal_entries_reversed_of_id",
            "reversed_of_id",
            unique=True,
            postgresql_where=text("reversed_of_id IS NOT NULL"),
        ),
    )


__all__ = ["JournalEntry"]
