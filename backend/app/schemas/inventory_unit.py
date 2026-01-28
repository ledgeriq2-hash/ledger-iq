from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.core.pagination import PaginatedResponse
from app.schemas.common import BaseSchema, IDTimestampMixin


class InventoryUnitBase(BaseSchema):
    code: str
    name: str
    ratio_to_base: Decimal = Field(..., gt=0)

    @field_validator("code")
    @classmethod
    def code_not_blank(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("code must not be blank")
        return cleaned

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned


class InventoryUnitCreate(InventoryUnitBase):
    pass


class InventoryUnitOut(IDTimestampMixin, InventoryUnitBase):
    id: UUID


class InventoryUnitListOut(PaginatedResponse[InventoryUnitOut]):
    pass


__all__ = [
    "InventoryUnitBase",
    "InventoryUnitCreate",
    "InventoryUnitOut",
    "InventoryUnitListOut",
]
