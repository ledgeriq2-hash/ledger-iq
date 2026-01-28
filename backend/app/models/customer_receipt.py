from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.customer import Customer

if TYPE_CHECKING:
    from app.models.customer_receipt_allocation import CustomerReceiptAllocation


class CustomerReceiptStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class CustomerReceipt(BaseModel):
    __tablename__ = "customer_receipts"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    receipt_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    status: Mapped[CustomerReceiptStatus] = mapped_column(
        SqlEnum(CustomerReceiptStatus, name="customer_receipt_status"),
        nullable=False,
        server_default=CustomerReceiptStatus.DRAFT.value,
    )
    amount_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    base_amount_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cash_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posting_journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversal_journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )

    customer: Mapped[Customer] = relationship("Customer", lazy="joined")
    allocations: Mapped[list["CustomerReceiptAllocation"]] = relationship(
        "CustomerReceiptAllocation",
        back_populates="receipt",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "receipt_no", name="uq_customer_receipts_tenant_receipt_no"),
        Index("ix_customer_receipts_tenant_id", "tenant_id"),
        Index("ix_customer_receipts_created_at", "created_at"),
        Index("ix_customer_receipts_customer_id", "customer_id"),
        Index("ix_customer_receipts_receipt_date", "receipt_date"),
        Index("ix_customer_receipts_status", "status"),
        Index("ix_customer_receipts_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_customer_receipts_tenant_status", "tenant_id", "status"),
    )


__all__ = ["CustomerReceipt", "CustomerReceiptStatus"]
