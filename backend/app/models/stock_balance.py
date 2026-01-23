from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.product import Product


class StockBalance(BaseModel):
    __tablename__ = "stock_balances"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    on_hand_qty_base: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
    )

    product: Mapped["Product"] = relationship("Product", lazy="joined")

    __table_args__ = (
        UniqueConstraint("tenant_id", "product_id", name="uq_stock_balances_tenant_product"),
        Index("ix_stock_balances_tenant_id", "tenant_id"),
        Index("ix_stock_balances_created_at", "created_at"),
        Index("ix_stock_balances_product_id", "product_id"),
    )


__all__ = ["StockBalance"]
