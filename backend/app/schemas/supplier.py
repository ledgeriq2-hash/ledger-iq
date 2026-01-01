from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.core.pagination import PaginatedResponse
from app.schemas.common import BaseSchema, IDTimestampMixin


class SupplierBase(BaseSchema):
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    balance: Decimal = Decimal("0")
    is_deleted: bool = False


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseSchema):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    balance: Decimal | None = None
    is_deleted: bool | None = None


class SupplierPublic(IDTimestampMixin, SupplierBase):
    id: UUID


class SupplierList(PaginatedResponse[SupplierPublic]):
    pass


__all__ = ["SupplierBase", "SupplierCreate", "SupplierUpdate", "SupplierPublic", "SupplierList"]
