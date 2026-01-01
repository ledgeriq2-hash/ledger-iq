from __future__ import annotations

from decimal import Decimal
import uuid

from sqlalchemy import ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.chart_of_account import ChartOfAccount
from app.models.journal_entry import JournalEntry


class JournalEntryLine(BaseModel):
    __tablename__ = "journal_entry_lines"

    journal_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chart_of_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    currency_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    line_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reference_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    journal_entry: Mapped[JournalEntry] = relationship("JournalEntry", back_populates="lines", lazy="joined")
    account: Mapped[ChartOfAccount] = relationship("ChartOfAccount", lazy="joined")

    __table_args__ = (
        Index("ix_journal_entry_lines_tenant_id", "tenant_id"),
        Index("ix_journal_entry_lines_created_at", "created_at"),
        Index("ix_journal_entry_lines_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_journal_entry_lines_journal_entry_id", "journal_entry_id"),
        Index("ix_journal_entry_lines_account_id", "account_id"),
        Index("ix_journal_entry_lines_reference", "reference_type", "reference_id"),
    )


__all__ = ["JournalEntryLine"]
