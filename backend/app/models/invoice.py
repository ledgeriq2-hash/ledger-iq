from __future__ import annotations

from datetime import date
import uuid
from enum import Enum
from decimal import Decimal

from sqlalchemy import Date, Enum as SqlEnum, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.customer import Customer


class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class Invoice(BaseModel):
    __tablename__ = "invoices"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        SqlEnum(InvoiceStatus, name="invoice_status"),
        nullable=False,
        server_default=InvoiceStatus.DRAFT.value,
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped[Customer] = relationship("Customer", lazy="joined")
    items: Mapped[list["InvoiceItem"]] = relationship("InvoiceItem", back_populates="invoice", lazy="selectin")

    __table_args__ = (
        Index("ix_invoices_tenant_id", "tenant_id"),
        Index("ix_invoices_created_at", "created_at"),
        Index("ix_invoices_customer_id", "customer_id"),
        Index("ix_invoices_issue_date", "issue_date"),
    )


__all__ = ["Invoice", "InvoiceStatus"]
