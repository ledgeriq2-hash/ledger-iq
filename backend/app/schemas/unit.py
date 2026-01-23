from __future__ import annotations

from uuid import UUID

from pydantic import field_validator

from app.core.pagination import PaginatedResponse
from app.schemas.common import BaseSchema, IDTimestampMixin


class UnitBase(BaseSchema):
    code: str
    name: str
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


class UnitCreate(UnitBase):
    pass


class UnitUpdate(BaseSchema):
    code: str | None = None
    name: str | None = None
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


class UnitOut(IDTimestampMixin, UnitBase):
    id: UUID


class UnitListOut(PaginatedResponse[UnitOut]):
    pass


__all__ = ["UnitBase", "UnitCreate", "UnitUpdate", "UnitOut", "UnitListOut"]
