from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class JournalLine(BaseModel):
    __tablename__ = "journal_lines"

    entry_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    debit_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
    )
    credit_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
    )
    line_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    debit_base: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
    )
    credit_base: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
    )
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    dimensions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tax_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    entry: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="ledger_lines", lazy="joined")
    account: Mapped["Account"] = relationship("Account", lazy="joined")

    __table_args__ = (
        UniqueConstraint("entry_id", "line_no", name="uq_journal_lines_entry_line"),
        Index("ix_journal_lines_tenant_id", "tenant_id"),
        Index("ix_journal_lines_created_at", "created_at"),
        Index("ix_journal_lines_entry_id", "entry_id"),
        Index("ix_journal_lines_account_id", "account_id"),
    )


__all__ = ["JournalLine"]
