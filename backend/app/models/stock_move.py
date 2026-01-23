from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.journal_entry import JournalEntry
    from app.models.product import Product
    from app.models.unit import Unit


class StockMoveDirection(str, Enum):
    IN = "IN"
    OUT = "OUT"


class StockMove(BaseModel):
    __tablename__ = "stock_moves"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    move_date: Mapped[date] = mapped_column(Date, nullable=False)
    direction: Mapped[StockMoveDirection] = mapped_column(
        SqlEnum(StockMoveDirection, name="stock_move_direction"),
        nullable=False,
    )
    quantity_base: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        server_default=text("0"),
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=True,
    )
    quantity_original: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    posted_journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )

    product: Mapped["Product"] = relationship("Product", lazy="joined")
    unit: Mapped["Unit | None"] = relationship("Unit", lazy="joined")
    posted_entry: Mapped["JournalEntry | None"] = relationship("JournalEntry", lazy="joined")

    __table_args__ = (
        Index("ix_stock_moves_tenant_id", "tenant_id"),
        Index("ix_stock_moves_created_at", "created_at"),
        Index("ix_stock_moves_tenant_product_date", "tenant_id", "product_id", "move_date"),
        Index("ix_stock_moves_tenant_reference", "tenant_id", "reference_type", "reference_id"),
        Index("ix_stock_moves_tenant_move_date", "tenant_id", "move_date"),
    )


__all__ = ["StockMove", "StockMoveDirection"]
