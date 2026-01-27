from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.purchase_invoice import PurchaseInvoice
    from app.models.vendor_payment import VendorPayment


class VendorPaymentAllocation(BaseModel):
    __tablename__ = "vendor_payment_allocations"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendor_payments.id", ondelete="CASCADE"),
        nullable=False,
    )
    purchase_bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_invoices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))

    payment: Mapped["VendorPayment"] = relationship(
        "VendorPayment", back_populates="allocations", lazy="joined"
    )
    purchase_bill: Mapped["PurchaseInvoice"] = relationship("PurchaseInvoice", lazy="joined")

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_vendor_payment_allocations_amount_positive"),
        UniqueConstraint(
            "tenant_id",
            "payment_id",
            "purchase_bill_id",
            name="uq_vendor_payment_allocations_tenant_payment_bill",
        ),
        Index("ix_vendor_payment_allocations_tenant_id", "tenant_id"),
        Index("ix_vendor_payment_allocations_created_at", "created_at"),
        Index("ix_vendor_payment_allocations_payment_id", "payment_id"),
        Index("ix_vendor_payment_allocations_purchase_bill_id", "purchase_bill_id"),
        Index("ix_vendor_payment_allocations_tenant_payment", "tenant_id", "payment_id"),
        Index("ix_vendor_payment_allocations_tenant_bill", "tenant_id", "purchase_bill_id"),
    )


__all__ = ["VendorPaymentAllocation"]
