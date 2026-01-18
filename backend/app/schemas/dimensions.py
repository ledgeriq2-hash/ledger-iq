from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.schemas.common import BaseSchema, IDTimestampMixin


class DimensionBase(BaseSchema):
    key: str
    name: str
    is_active: bool = True


class DimensionCreate(BaseSchema):
    key: str
    name: str


class DimensionUpdate(BaseSchema):
    key: str | None = None
    name: str | None = None


class DimensionPublic(IDTimestampMixin, DimensionBase):
    pass


class DimensionList(BaseSchema):
    items: list[DimensionPublic]


class DimensionValueBase(BaseSchema):
    dimension_id: UUID
    code: str
    name: str
    is_active: bool = True


class DimensionValueCreate(BaseSchema):
    code: str
    name: str


class DimensionValueUpdate(BaseSchema):
    code: str | None = None
    name: str | None = None


class DimensionValuePublic(IDTimestampMixin, DimensionValueBase):
    pass


class DimensionValueList(BaseSchema):
    items: list[DimensionValuePublic]


class JournalLineDimensionItem(BaseSchema):
    dimension_id: UUID
    dimension_key: str
    dimension_name: str
    value_id: UUID
    value_code: str
    value_name: str


class JournalLineDimensionsUpdate(BaseSchema):
    dimensions: dict[str, UUID] = Field(default_factory=dict)


class JournalLineDimensionsResponse(BaseSchema):
    journal_line_id: UUID
    items: list[JournalLineDimensionItem]


__all__ = [
    "DimensionBase",
    "DimensionCreate",
    "DimensionUpdate",
    "DimensionPublic",
    "DimensionList",
    "DimensionValueBase",
    "DimensionValueCreate",
    "DimensionValueUpdate",
    "DimensionValuePublic",
    "DimensionValueList",
    "JournalLineDimensionItem",
    "JournalLineDimensionsUpdate",
    "JournalLineDimensionsResponse",
]
