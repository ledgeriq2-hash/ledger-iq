from __future__ import annotations

from decimal import Decimal
from typing import List
from uuid import UUID

from pydantic import field_validator

from app.schemas.common import BaseSchema, IDTimestampMixin


class CustomerBase(BaseSchema):
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    balance: Decimal = Decimal("0")
    is_deleted: bool = False

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("name must not be blank")
        return value


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseSchema):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    balance: Decimal | None = None
    is_deleted: bool | None = None


class CustomerPublic(IDTimestampMixin, CustomerBase):
    id: UUID


class CustomerList(BaseSchema):
    items: List[CustomerPublic]
    page: int = 1
    page_size: int = 50
    total: int = 0
    pages: int = 0


__all__ = ["CustomerBase", "CustomerCreate", "CustomerUpdate", "CustomerPublic", "CustomerList"]
