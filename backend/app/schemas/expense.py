from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from app.schemas.common import BaseSchema, IDTimestampMixin


class ExpenseBase(BaseSchema):
    supplier_id: UUID
    category: str
    amount: Decimal
    currency: str
    expense_date: date
    description: str | None = None
    product_id: UUID | None = None
    quantity: Decimal | None = None


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseSchema):
    supplier_id: UUID | None = None
    category: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    expense_date: date | None = None
    description: str | None = None


class ExpensePublic(IDTimestampMixin, ExpenseBase):
    id: UUID


class ExpenseList(BaseSchema):
    items: list[ExpensePublic]
    page: int = 1
    page_size: int = 50
    total: int = 0
    pages: int = 0


__all__ = ["ExpenseBase", "ExpenseCreate", "ExpenseUpdate", "ExpensePublic", "ExpenseList"]
