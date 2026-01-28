from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.core.pagination import PaginatedResponse
from app.models.stock_move import StockMoveDirection, StockMoveSourceType
from app.schemas.common import BaseSchema, IDTimestampMixin


class StockMoveBase(BaseSchema):
    product_id: UUID
    quantity: Decimal
    unit_id: UUID | None = None
    base_quantity: Decimal
    direction: StockMoveDirection
    source_type: StockMoveSourceType
    source_id: UUID
    posting_journal_entry_id: UUID | None = None
    posted_at: datetime
    reversed_stock_move_id: UUID | None = None


class StockMoveCreate(StockMoveBase):
    pass


class StockMoveOut(IDTimestampMixin, StockMoveBase):
    id: UUID


class StockMoveListOut(PaginatedResponse[StockMoveOut]):
    pass


class StockLedgerListOut(PaginatedResponse[StockMoveOut]):
    pass


class StockBalanceOut(BaseSchema):
    product_id: UUID
    base_quantity: Decimal


class StockBalanceListOut(PaginatedResponse[StockBalanceOut]):
    pass


__all__ = [
    "StockMoveBase",
    "StockMoveCreate",
    "StockMoveOut",
    "StockMoveListOut",
    "StockLedgerListOut",
    "StockBalanceOut",
    "StockBalanceListOut",
    "StockMoveDirection",
    "StockMoveSourceType",
]
