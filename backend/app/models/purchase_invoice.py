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
    from app.models.purchase_invoice_line import PurchaseInvoiceLine


class PurchaseInvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class PurchaseInvoice(BaseModel):
    __tablename__ = "purchase_invoices"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    invoice_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[PurchaseInvoiceStatus] = mapped_column(
        SqlEnum(PurchaseInvoiceStatus, name="purchase_invoice_status"),
        nullable=False,
        server_default=PurchaseInvoiceStatus.DRAFT.value,
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posting_journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    reversal_journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )

    vendor: Mapped[Vendor] = relationship("Vendor", lazy="joined")
    lines: Mapped[list["PurchaseInvoiceLine"]] = relationship(
        "PurchaseInvoiceLine",
        back_populates="invoice",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_no", name="uq_purchase_invoices_tenant_invoice_no"),
        Index("ix_purchase_invoices_tenant_id", "tenant_id"),
        Index("ix_purchase_invoices_created_at", "created_at"),
        Index("ix_purchase_invoices_vendor_id", "vendor_id"),
        Index("ix_purchase_invoices_invoice_date", "invoice_date"),
        Index("ix_purchase_invoices_status", "status"),
        Index("ix_purchase_invoices_tenant_vendor", "tenant_id", "vendor_id"),
        Index("ix_purchase_invoices_tenant_status", "tenant_id", "status"),
    )


__all__ = ["PurchaseInvoice", "PurchaseInvoiceStatus"]
