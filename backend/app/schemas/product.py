from __future__ import annotations

from decimal import Decimal
from typing import List
from uuid import UUID

from pydantic import field_validator

from app.schemas.common import BaseSchema, IDTimestampMixin


class ProductBase(BaseSchema):
    name: str
    sku: str | None = None
    unit_price: Decimal = Decimal("0")
    cost_price: Decimal = Decimal("0")
    stock_quantity: Decimal = Decimal("0")
    is_service: bool = False
    category: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseSchema):
    name: str | None = None
    sku: str | None = None
    unit_price: Decimal | None = None
    cost_price: Decimal | None = None
    stock_quantity: Decimal | None = None
    is_service: bool | None = None
    category: str | None = None


class ProductPublic(IDTimestampMixin, ProductBase):
    id: UUID


class ProductList(BaseSchema):
    items: List[ProductPublic]


__all__ = ["ProductBase", "ProductCreate", "ProductUpdate", "ProductPublic", "ProductList"]
