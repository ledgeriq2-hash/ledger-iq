from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.account import Account
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.sales_invoice import SalesInvoice
    from app.models.unit import Unit


class SalesInvoiceLine(BaseModel):
    __tablename__ = "sales_invoice_lines"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales_invoices.id", ondelete="CASCADE"),
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
    revenue_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )

    invoice: Mapped["SalesInvoice"] = relationship("SalesInvoice", back_populates="lines", lazy="joined")
    revenue_account: Mapped[Account] = relationship("Account", lazy="joined")
    product: Mapped["Product | None"] = relationship("Product", lazy="joined")
    unit: Mapped["Unit | None"] = relationship("Unit", lazy="joined")

    __table_args__ = (
        Index("ix_sales_invoice_lines_tenant_id", "tenant_id"),
        Index("ix_sales_invoice_lines_created_at", "created_at"),
        Index("ix_sales_invoice_lines_invoice_id", "invoice_id"),
        Index("ix_sales_invoice_lines_revenue_account_id", "revenue_account_id"),
        Index("ix_sales_invoice_lines_product_id", "product_id"),
    )


__all__ = ["SalesInvoiceLine"]
