from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer_receipt import CustomerReceipt
    from app.models.sales_invoice import SalesInvoice


class CustomerReceiptAllocation(BaseModel):
    __tablename__ = "customer_receipt_allocations"

    receipt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_receipts.id", ondelete="CASCADE"),
        nullable=False,
    )
    sales_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_invoices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))

    receipt: Mapped["CustomerReceipt"] = relationship(
        "CustomerReceipt", back_populates="allocations", lazy="joined"
    )
    sales_invoice: Mapped["SalesInvoice"] = relationship("SalesInvoice", lazy="joined")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_customer_receipt_allocations_amount_positive"),
        UniqueConstraint(
            "tenant_id",
            "receipt_id",
            "sales_invoice_id",
            name="uq_customer_receipt_allocations_tenant_receipt_invoice",
        ),
        Index("ix_customer_receipt_allocations_tenant_id", "tenant_id"),
        Index("ix_customer_receipt_allocations_created_at", "created_at"),
        Index("ix_customer_receipt_allocations_receipt_id", "receipt_id"),
        Index("ix_customer_receipt_allocations_sales_invoice_id", "sales_invoice_id"),
        Index("ix_customer_receipt_allocations_tenant_receipt", "tenant_id", "receipt_id"),
        Index("ix_customer_receipt_allocations_tenant_invoice", "tenant_id", "sales_invoice_id"),
    )


__all__ = ["CustomerReceiptAllocation"]
