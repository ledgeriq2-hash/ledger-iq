from __future__ import annotations

from decimal import Decimal
from typing import List
from uuid import UUID

from pydantic import Field, field_validator

from app.models.stock_movement import MovementType, ReferenceType
from app.schemas.common import BaseSchema, IDTimestampMixin
from app.schemas.product import ProductPublic


class StockMovementBase(BaseSchema):
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    movement_type: MovementType
    reference_type: ReferenceType | None = None
    reference_id: UUID | None = None

    @field_validator("movement_type")
    @classmethod
    def normalize_type(cls, value: MovementType) -> MovementType:
        return MovementType(value)


class StockMovementCreate(StockMovementBase):
    pass


class StockMovementUpdate(BaseSchema):
    quantity: Decimal | None = Field(default=None, gt=0)
    movement_type: MovementType | None = None


class StockMovementPublic(IDTimestampMixin, StockMovementBase):
    id: UUID
    product: ProductPublic | None = None


class StockMovementList(BaseSchema):
    items: List[StockMovementPublic]
    page: int = 1
    page_size: int = 50
    total: int = 0
    pages: int = 0


class InventorySummaryItem(BaseSchema):
    product_id: UUID
    product_name: str
    sku: str | None = None
    stock_quantity: Decimal
    cost_price: Decimal
    valuation: Decimal


class InventorySummaryResponse(BaseSchema):
    items: List[InventorySummaryItem]
    total_value: Decimal


__all__ = [
    "StockMovementCreate",
    "StockMovementUpdate",
    "StockMovementPublic",
    "StockMovementList",
    "InventorySummaryResponse",
    "InventorySummaryItem",
]
