from __future__ import annotations

from uuid import UUID

from decimal import Decimal

from pydantic import Field, field_validator

from app.core.pagination import PaginatedResponse
from app.schemas.common import BaseSchema, IDTimestampMixin


class UnitBase(BaseSchema):
    code: str
    name: str
    ratio_to_base: Decimal = Field(default=Decimal("1"))
    is_base: bool = False

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

    @field_validator("ratio_to_base")
    @classmethod
    def ratio_positive(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) <= 0:
            raise ValueError("ratio_to_base must be greater than zero")
        return value


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseSchema):
    code: str | None = None
    name: str | None = None
    ratio_to_base: Decimal | None = None
    is_base: bool | None = None

    @field_validator("code")
    @classmethod
    def update_code_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("code must not be blank")
        return cleaned

    @field_validator("name")
    @classmethod
    def update_name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned

    @field_validator("ratio_to_base")
    @classmethod
    def update_ratio_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) <= 0:
            raise ValueError("ratio_to_base must be greater than zero")
        return value


class UnitOut(IDTimestampMixin, UnitBase):
    id: UUID


class UnitListOut(PaginatedResponse[UnitOut]):
    pass


__all__ = ["UnitBase", "UnitCreate", "UnitUpdate", "UnitOut", "UnitListOut"]
