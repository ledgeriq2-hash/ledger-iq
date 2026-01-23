from __future__ import annotations

from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.pagination import PaginatedResponse
from app.models.product import ProductStatus
from app.schemas.common import BaseSchema, IDTimestampMixin


class ProductBase(BaseSchema):
    model_config = {"from_attributes": True, "populate_by_name": True}

    sku: str
    name: str
    status: ProductStatus = ProductStatus.ACTIVE
    base_unit_id: UUID
    notes: str | None = None
    metadata_json: dict | None = Field(default=None, serialization_alias="metadata")

    @model_validator(mode="before")
    @classmethod
    def normalize_metadata(cls, data: object) -> object:
        if isinstance(data, dict) and "metadata" in data and "metadata_json" not in data:
            updated = dict(data)
            updated["metadata_json"] = updated.pop("metadata")
            return updated
        return data

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator("sku")
    @classmethod
    def sku_not_blank(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("sku must not be blank")
        return value


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseSchema):
    model_config = {"from_attributes": True, "populate_by_name": True}

    sku: str | None = None
    name: str | None = None
    status: ProductStatus | None = None
    base_unit_id: UUID | None = None
    notes: str | None = None
    metadata_json: dict | None = Field(default=None, serialization_alias="metadata")

    @model_validator(mode="before")
    @classmethod
    def normalize_metadata(cls, data: object) -> object:
        if isinstance(data, dict) and "metadata" in data and "metadata_json" not in data:
            updated = dict(data)
            updated["metadata_json"] = updated.pop("metadata")
            return updated
        return data

    @field_validator("name")
    @classmethod
    def update_name_not_blank(cls, v: str | None) -> str | None:
        if v is None:
            return v
        value = v.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator("sku")
    @classmethod
    def update_sku_not_blank(cls, v: str | None) -> str | None:
        if v is None:
            return v
        value = v.strip()
        if not value:
            raise ValueError("sku must not be blank")
        return value


class ProductPublic(IDTimestampMixin, ProductBase):
    model_config = {"from_attributes": True, "populate_by_name": True}

    id: UUID


class ProductOut(ProductPublic):
    pass


class ProductListOut(PaginatedResponse[ProductOut]):
    pass


__all__ = [
    "ProductBase",
    "ProductCreate",
    "ProductUpdate",
    "ProductPublic",
    "ProductOut",
    "ProductListOut",
    "ProductStatus",
]
