from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from enum import Enum

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Date, ForeignKey, Index, Numeric, text
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
    event_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=text("CURRENT_DATE"))

    product: Mapped[Product] = relationship("Product", lazy="joined")

    __table_args__ = (
        Index("ix_stock_movements_tenant_id", "tenant_id"),
        Index("ix_stock_movements_created_at", "created_at"),
        Index("ix_stock_movements_event_date", "event_date"),
        Index("ix_stock_movements_product_id", "product_id"),
    )


__all__ = ["StockMovement", "MovementType", "ReferenceType"]
