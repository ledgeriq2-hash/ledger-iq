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
    from app.models.sales_invoice_line import SalesInvoiceLine


class SalesInvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    POSTED = "POSTED"
    REVERSED = "REVERSED"


class SalesInvoice(BaseModel):
    __tablename__ = "sales_invoices"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    invoice_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    status: Mapped[SalesInvoiceStatus] = mapped_column(
        SqlEnum(SalesInvoiceStatus, name="sales_invoice_status"),
        nullable=False,
        server_default=SalesInvoiceStatus.DRAFT.value,
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    vat_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    base_subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    base_vat_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    base_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    memo: Mapped[str | None] = mapped_column(String(255), nullable=True)
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

    customer: Mapped[Customer] = relationship("Customer", lazy="joined")
    lines: Mapped[list["SalesInvoiceLine"]] = relationship(
        "SalesInvoiceLine",
        back_populates="invoice",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "invoice_no", name="uq_sales_invoices_tenant_invoice_no"),
        Index("ix_sales_invoices_tenant_id", "tenant_id"),
        Index("ix_sales_invoices_created_at", "created_at"),
        Index("ix_sales_invoices_customer_id", "customer_id"),
        Index("ix_sales_invoices_invoice_date", "invoice_date"),
        Index("ix_sales_invoices_status", "status"),
        Index("ix_sales_invoices_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_sales_invoices_tenant_status", "tenant_id", "status"),
    )


__all__ = ["SalesInvoice", "SalesInvoiceStatus"]
