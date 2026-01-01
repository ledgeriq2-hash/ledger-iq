from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import field_validator

from app.core.pagination import PaginatedResponse
from app.models.supplier import SupplierStatus
from app.schemas.common import BaseSchema, IDTimestampMixin


class SupplierBase(BaseSchema):
    model_config = {"from_attributes": True}

    code: str
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    balance: Decimal = Decimal("0")

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


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseSchema):
    model_config = {"from_attributes": True}

    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    balance: Decimal | None = None

    @field_validator("name")
    @classmethod
    def update_name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned


class SupplierPublic(IDTimestampMixin, SupplierBase):
    id: UUID
    status: SupplierStatus = SupplierStatus.ACTIVE
    deleted_at: datetime | None = None
    deactivated_at: datetime | None = None


class SupplierStatusFilter(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DELETED = "DELETED"
    ALL = "ALL"


class SupplierStatusUpdate(BaseSchema):
    status: SupplierStatus


class SupplierListResponse(PaginatedResponse[SupplierPublic]):
    pass


__all__ = [
    "SupplierBase",
    "SupplierCreate",
    "SupplierUpdate",
    "SupplierPublic",
    "SupplierStatus",
    "SupplierStatusFilter",
    "SupplierStatusUpdate",
    "SupplierListResponse",
]
