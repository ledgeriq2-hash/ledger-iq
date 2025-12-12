from __future__ import annotations

from decimal import Decimal
import uuid
from enum import Enum

from sqlalchemy import Enum as SqlEnum, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.product import Product


class MovementType(str, Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"


class ReferenceType(str, Enum):
    INVOICE = "INVOICE"
    PURCHASE = "PURCHASE"
    MANUAL = "MANUAL"


class StockMovement(BaseModel):
    __tablename__ = "stock_movements"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    movement_type: Mapped[MovementType] = mapped_column(
        SqlEnum(MovementType, name="stock_movement_type"),
        nullable=False,
    )
    reference_type: Mapped[ReferenceType | None] = mapped_column(
        SqlEnum(ReferenceType, name="stock_movement_reference_type"),
        nullable=True,
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    product: Mapped[Product] = relationship("Product", lazy="joined")

    __table_args__ = (
        Index("ix_stock_movements_tenant_id", "tenant_id"),
        Index("ix_stock_movements_created_at", "created_at"),
        Index("ix_stock_movements_product_id", "product_id"),
    )


__all__ = ["StockMovement", "MovementType", "ReferenceType"]
