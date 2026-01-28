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
from app.models.vendor import Vendor

if TYPE_CHECKING:
    from app.models.vendor_payment_allocation import VendorPaymentAllocation


class VendorPaymentStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class VendorPayment(BaseModel):
    __tablename__ = "vendor_payments"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payment_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    status: Mapped[VendorPaymentStatus] = mapped_column(
        SqlEnum(VendorPaymentStatus, name="vendor_payment_status"),
        nullable=False,
        server_default=VendorPaymentStatus.DRAFT.value,
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

    vendor: Mapped[Vendor] = relationship("Vendor", lazy="joined")
    allocations: Mapped[list["VendorPaymentAllocation"]] = relationship(
        "VendorPaymentAllocation",
        back_populates="payment",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "payment_no", name="uq_vendor_payments_tenant_payment_no"),
        Index("ix_vendor_payments_tenant_id", "tenant_id"),
        Index("ix_vendor_payments_created_at", "created_at"),
        Index("ix_vendor_payments_vendor_id", "vendor_id"),
        Index("ix_vendor_payments_payment_date", "payment_date"),
        Index("ix_vendor_payments_status", "status"),
        Index("ix_vendor_payments_tenant_vendor", "tenant_id", "vendor_id"),
        Index("ix_vendor_payments_tenant_status", "tenant_id", "status"),
    )


__all__ = ["VendorPayment", "VendorPaymentStatus"]
