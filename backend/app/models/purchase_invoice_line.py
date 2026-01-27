from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Numeric, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.account import Account
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.purchase_invoice import PurchaseInvoice
    from app.models.unit import Unit


class PurchaseInvoiceLine(BaseModel):
    __tablename__ = "purchase_invoice_lines"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="SET NULL"),
        nullable=True,
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    expense_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )

    invoice: Mapped["PurchaseInvoice"] = relationship("PurchaseInvoice", back_populates="lines", lazy="joined")
    expense_account: Mapped[Account] = relationship("Account", lazy="joined")
    product: Mapped["Product | None"] = relationship("Product", lazy="joined")
    unit: Mapped["Unit | None"] = relationship("Unit", lazy="joined")

    @property
    def line_total(self) -> Decimal:
        return self.amount

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "invoice_id",
            "line_no",
            name="uq_purchase_invoice_lines_tenant_invoice_line_no",
        ),
        Index("ix_purchase_invoice_lines_tenant_id", "tenant_id"),
        Index("ix_purchase_invoice_lines_created_at", "created_at"),
        Index("ix_purchase_invoice_lines_invoice_id", "invoice_id"),
        Index("ix_purchase_invoice_lines_tenant_invoice", "tenant_id", "invoice_id"),
        Index("ix_purchase_invoice_lines_expense_account_id", "expense_account_id"),
        Index("ix_purchase_invoice_lines_product_id", "product_id"),
    )


__all__ = ["PurchaseInvoiceLine"]
