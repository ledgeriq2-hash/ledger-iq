from __future__ import annotations

from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.pagination import PaginatedResponse
from app.models.vendor import VendorStatus
from app.schemas.common import BaseSchema, IDTimestampMixin


class VendorBase(BaseSchema):
    model_config = {"from_attributes": True, "populate_by_name": True}

    code: str
    name: str
    status: VendorStatus = VendorStatus.ACTIVE
    currency_code: str | None = None
    payment_terms_days: int | None = None
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


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseSchema):
    model_config = {"from_attributes": True, "populate_by_name": True}

    code: str | None = None
    name: str | None = None
    status: VendorStatus | None = None
    currency_code: str | None = None
    payment_terms_days: int | None = None
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


class VendorOut(IDTimestampMixin, VendorBase):
    model_config = {"from_attributes": True, "populate_by_name": True}

    id: UUID


class VendorListOut(PaginatedResponse[VendorOut]):
    pass


__all__ = [
    "VendorBase",
    "VendorCreate",
    "VendorUpdate",
    "VendorOut",
    "VendorListOut",
    "VendorStatus",
]
