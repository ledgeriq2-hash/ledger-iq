from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List
from uuid import UUID

from app.models.invoice import InvoiceStatus
from app.schemas.common import BaseSchema, IDTimestampMixin


class InvoiceItemBase(BaseSchema):
    product_id: UUID | None = None
    description: str | None = None
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    line_total: Decimal


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemUpdate(BaseSchema):
    product_id: UUID | None = None
    description: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    tax_rate: Decimal | None = None
    line_total: Decimal | None = None


class InvoiceItemPublic(IDTimestampMixin, InvoiceItemBase):
    id: UUID


class InvoiceBase(BaseSchema):
    customer_id: UUID
    issue_date: date
    due_date: date | None = None
    status: InvoiceStatus = InvoiceStatus.DRAFT
    currency: str
    total_amount: Decimal = Decimal("0")
    notes: str | None = None


class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate] | None = None


class InvoiceUpdate(BaseSchema):
    customer_id: UUID | None = None
    issue_date: date | None = None
    due_date: date | None = None
    status: InvoiceStatus | None = None
    currency: str | None = None
    total_amount: Decimal | None = None
    notes: str | None = None
    items: List[InvoiceItemUpdate] | None = None


class InvoicePublic(IDTimestampMixin, InvoiceBase):
    id: UUID
    items: List[InvoiceItemPublic] | None = None


class InvoiceList(BaseSchema):
    items: List[InvoicePublic]
    page: int = 1
    page_size: int = 50
    total: int = 0
    pages: int = 0


__all__ = [
    "InvoiceBase",
    "InvoiceCreate",
    "InvoiceUpdate",
    "InvoicePublic",
    "InvoiceList",
    "InvoiceItemBase",
    "InvoiceItemCreate",
    "InvoiceItemUpdate",
    "InvoiceItemPublic",
]
