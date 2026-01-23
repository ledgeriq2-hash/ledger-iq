from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.core.pagination import PaginatedResponse
from app.models.stock_move import StockMoveDirection
from app.schemas.common import BaseSchema, IDTimestampMixin


class StockMoveBase(BaseSchema):
    product_id: UUID
    move_date: date
    direction: StockMoveDirection
    quantity_base: Decimal = Field(..., gt=0)
    unit_id: UUID | None = None
    quantity_original: Decimal | None = None
    reference_type: str
    reference_id: UUID

    @field_validator("quantity_base")
    @classmethod
    def quantity_base_positive(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) <= 0:
            raise ValueError("quantity_base must be greater than zero")
        return value

    @field_validator("quantity_original")
    @classmethod
    def quantity_original_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) <= 0:
            raise ValueError("quantity_original must be greater than zero")
        return value

    @field_validator("reference_type")
    @classmethod
    def reference_type_not_blank(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("reference_type must not be blank")
        return cleaned


class StockMoveCreate(StockMoveBase):
    pass


class StockMoveOut(IDTimestampMixin, StockMoveBase):
    id: UUID
    posted_journal_entry_id: UUID | None = None


class StockMoveListOut(PaginatedResponse[StockMoveOut]):
    pass


class StockBalanceOut(IDTimestampMixin, BaseSchema):
    product_id: UUID
    on_hand_qty_base: Decimal
    updated_at: datetime


class StockBalanceListOut(PaginatedResponse[StockBalanceOut]):
    pass


__all__ = [
    "StockMoveBase",
    "StockMoveCreate",
    "StockMoveOut",
    "StockMoveListOut",
    "StockBalanceOut",
    "StockBalanceListOut",
    "StockMoveDirection",
]
