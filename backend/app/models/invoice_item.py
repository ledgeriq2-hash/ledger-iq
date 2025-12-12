from __future__ import annotations

from decimal import Decimal
import uuid

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.invoice import Invoice
from app.models.product import Product


class InvoiceItem(BaseModel):
    __tablename__ = "invoice_items"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default=text("0"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default=text("0"))

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="items", lazy="joined")
    product: Mapped[Product | None] = relationship("Product", lazy="joined")

    __table_args__ = (
        Index("ix_invoice_items_tenant_id", "tenant_id"),
        Index("ix_invoice_items_created_at", "created_at"),
        Index("ix_invoice_items_invoice_id", "invoice_id"),
    )


__all__ = ["InvoiceItem"]
