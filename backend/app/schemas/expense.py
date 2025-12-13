from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List
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
    items: List[ExpensePublic]


__all__ = ["ExpenseBase", "ExpenseCreate", "ExpenseUpdate", "ExpensePublic", "ExpenseList"]
