from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.core.pagination import PaginatedResponse
from app.schemas.common import BaseSchema, IDTimestampMixin


class UnitConversionBase(BaseSchema):
    from_unit_id: UUID
    to_unit_id: UUID
    multiplier: Decimal = Field(..., gt=0)

    @field_validator("multiplier")
    @classmethod
    def multiplier_positive(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) <= 0:
            raise ValueError("multiplier must be greater than zero")
        return value


class UnitConversionCreate(UnitConversionBase):
    pass


class UnitConversionUpdate(BaseSchema):
    multiplier: Decimal | None = Field(default=None, gt=0)

    @field_validator("multiplier")
    @classmethod
    def multiplier_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) <= 0:
            raise ValueError("multiplier must be greater than zero")
        return value


class UnitConversionOut(IDTimestampMixin, UnitConversionBase):
    id: UUID


class UnitConversionListOut(PaginatedResponse[UnitConversionOut]):
    pass


__all__ = [
    "UnitConversionBase",
    "UnitConversionCreate",
    "UnitConversionUpdate",
    "UnitConversionOut",
    "UnitConversionListOut",
]
