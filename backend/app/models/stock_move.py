from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.journal_entry import JournalEntry
    from app.models.product import Product
    from app.models.unit import InventoryUnit


class StockMoveDirection(str, Enum):
    IN = "IN"
    OUT = "OUT"


class StockMoveSourceType(str, Enum):
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    REVERSAL = "REVERSAL"


class StockMove(BaseModel):
    __tablename__ = "stock_moves"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
        server_default=text("0"),
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_units.id", ondelete="RESTRICT"),
        nullable=True,
    )
    base_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6),
        nullable=False,
        server_default=text("0"),
    )
    source_type: Mapped[StockMoveSourceType] = mapped_column(
        SqlEnum(StockMoveSourceType, name="stock_move_source_type"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    posting_journal_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        "posted_journal_entry_id",
        UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    reversed_stock_move_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_moves.id", ondelete="SET NULL"),
        nullable=True,
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
    quantity_original: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    product: Mapped["Product"] = relationship("Product", lazy="joined")
    unit: Mapped["InventoryUnit | None"] = relationship("InventoryUnit", lazy="joined")
    posted_entry: Mapped["JournalEntry | None"] = relationship("JournalEntry", lazy="joined")

    __table_args__ = (
        Index("ix_stock_moves_tenant_id", "tenant_id"),
        Index("ix_stock_moves_created_at", "created_at"),
        Index("ix_stock_moves_tenant_product_date", "tenant_id", "product_id", "move_date"),
        Index("ix_stock_moves_tenant_reference", "tenant_id", "reference_type", "reference_id"),
        Index("ix_stock_moves_tenant_move_date", "tenant_id", "move_date"),
        Index("ix_stock_moves_tenant_source", "tenant_id", "source_type", "source_id"),
        Index("ix_stock_moves_tenant_product_posted", "tenant_id", "product_id", "posted_at"),
    )


__all__ = ["StockMove", "StockMoveDirection", "StockMoveSourceType"]
