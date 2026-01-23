from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class CashTransactionType(str, Enum):
    RECEIPT = "RECEIPT"
    PAYMENT = "PAYMENT"
    TRANSFER = "TRANSFER"


class CashTransactionStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class TreasuryCashTransaction(BaseModel):
    __tablename__ = "treasury_cash_transactions"

    transaction_type: Mapped[CashTransactionType] = mapped_column(
        SqlEnum(CashTransactionType, name="treasury_cash_transaction_type"),
        nullable=False,
    )
    status: Mapped[CashTransactionStatus] = mapped_column(
        SqlEnum(CashTransactionStatus, name="treasury_cash_transaction_status"),
        nullable=False,
        server_default=text("'DRAFT'"),
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    posting_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE"),
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    cash_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treasury_cash_accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    counterparty_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    from_cash_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treasury_cash_accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    to_cash_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("treasury_cash_accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )

    journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    reversal_journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_treasury_cash_transactions_tenant_id", "tenant_id"),
        Index("ix_treasury_cash_transactions_created_at", "created_at"),
        Index("ix_treasury_cash_transactions_posting_date", "posting_date"),
        Index("ix_treasury_cash_transactions_status", "status"),
        Index("ix_treasury_cash_transactions_transaction_type", "transaction_type"),
        Index("ix_treasury_cash_transactions_cash_account_id", "cash_account_id"),
        Index("ix_treasury_cash_transactions_from_cash_account_id", "from_cash_account_id"),
        Index("ix_treasury_cash_transactions_to_cash_account_id", "to_cash_account_id"),
        Index("ix_treasury_cash_transactions_counterparty_account_id", "counterparty_account_id"),
        Index("ix_treasury_cash_transactions_journal_entry_id", "journal_entry_id"),
        Index("ix_treasury_cash_transactions_reversal_journal_entry_id", "reversal_journal_entry_id"),
        CheckConstraint("amount > 0", name="ck_treasury_cash_transactions_amount_positive"),
        CheckConstraint(
            "(transaction_type IN ('RECEIPT', 'PAYMENT') AND cash_account_id IS NOT NULL "
            "AND counterparty_account_id IS NOT NULL AND from_cash_account_id IS NULL "
            "AND to_cash_account_id IS NULL) "
            "OR (transaction_type = 'TRANSFER' AND from_cash_account_id IS NOT NULL "
            "AND to_cash_account_id IS NOT NULL AND from_cash_account_id <> to_cash_account_id "
            "AND cash_account_id IS NULL AND counterparty_account_id IS NULL)",
            name="ck_treasury_cash_transactions_type_accounts",
        ),
    )


__all__ = ["CashTransactionType", "CashTransactionStatus", "TreasuryCashTransaction"]
