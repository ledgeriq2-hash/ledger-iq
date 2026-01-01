from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.schemas.common import BaseSchema, IDTimestampMixin


class EmployeeBase(BaseSchema):
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    balance: Decimal = Decimal("0")
    is_deleted: bool = False


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseSchema):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    tax_id: str | None = None
    balance: Decimal | None = None
    is_deleted: bool | None = None


class EmployeePublic(IDTimestampMixin, EmployeeBase):
    id: UUID


__all__ = ["EmployeeBase", "EmployeeCreate", "EmployeeUpdate", "EmployeePublic"]
