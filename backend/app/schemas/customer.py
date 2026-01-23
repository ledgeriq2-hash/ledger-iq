from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.pagination import PaginatedResponse
from app.models.customer import CustomerStatus
from app.schemas.common import BaseSchema, IDTimestampMixin


class CustomerBase(BaseSchema):
    model_config = {"from_attributes": True, "populate_by_name": True}

    code: str
    name: str
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None
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
    def code_not_blank(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("code must not be blank")
        return value

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class CustomerCreate(CustomerBase):
    status: CustomerStatus = CustomerStatus.ACTIVE


class CustomerUpdate(BaseSchema):
    model_config = {"from_attributes": True, "populate_by_name": True}

    code: str | None = None
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = None
    currency_code: str | None = None
    payment_terms_days: int | None = None
    notes: str | None = None
    status: CustomerStatus | None = None
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

    @field_validator("code")
    @classmethod
    def update_code_not_blank(cls, v: str | None) -> str | None:
        if v is None:
            return v
        value = v.strip()
        if not value:
            raise ValueError("code must not be blank")
        return value


class CustomerPublic(IDTimestampMixin, CustomerBase):
    model_config = {"from_attributes": True, "populate_by_name": True}

    id: UUID
    status: CustomerStatus = CustomerStatus.ACTIVE
    deleted_at: datetime | None = None


class CustomerOut(CustomerPublic):
    pass


class CustomerStatusFilter(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DELETED = "DELETED"
    ALL = "ALL"


class CustomerListOut(PaginatedResponse[CustomerOut]):
    pass


__all__ = [
    "CustomerBase",
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerPublic",
    "CustomerOut",
    "CustomerStatus",
    "CustomerStatusFilter",
    "CustomerListOut",
]
