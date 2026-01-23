from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_validator

from app.core.pagination import PaginatedResponse
from app.models.sales_invoice import SalesInvoiceStatus
from app.schemas.common import BaseSchema, IDTimestampMixin


class SalesInvoiceLineBase(BaseSchema):
    line_no: int
    description: str | None = None
    product_id: UUID | None = None
    unit_id: UUID | None = None
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    revenue_account_id: UUID

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) <= 0:
            raise ValueError("quantity must be greater than zero")
        return value

    @field_validator("unit_price", "amount")
    @classmethod
    def non_negative_amounts(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) < 0:
            raise ValueError("value must be non-negative")
        return value


class SalesInvoiceLineCreate(SalesInvoiceLineBase):
    pass


class SalesInvoiceLineUpdate(BaseSchema):
    line_no: int | None = None
    description: str | None = None
    product_id: UUID | None = None
    unit_id: UUID | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None
    revenue_account_id: UUID | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) <= 0:
            raise ValueError("quantity must be greater than zero")
        return value

    @field_validator("unit_price", "amount")
    @classmethod
    def non_negative_amounts(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if Decimal(str(value)) < 0:
            raise ValueError("value must be non-negative")
        return value


class SalesInvoiceLineOut(IDTimestampMixin, SalesInvoiceLineBase):
    id: UUID


class SalesInvoiceBase(BaseSchema):
    customer_id: UUID
    invoice_no: str
    invoice_date: date
    currency_code: str | None = None

    @field_validator("invoice_no")
    @classmethod
    def invoice_no_not_blank(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError("invoice_no must not be blank")
        return cleaned


class SalesInvoiceCreate(SalesInvoiceBase):
    lines: list[SalesInvoiceLineCreate] = Field(..., min_length=1)


class SalesInvoiceUpdate(BaseSchema):
    customer_id: UUID | None = None
    invoice_no: str | None = None
    invoice_date: date | None = None
    currency_code: str | None = None
    lines: list[SalesInvoiceLineUpdate] | None = Field(default=None, min_length=1)

    @field_validator("invoice_no")
    @classmethod
    def update_invoice_no_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("invoice_no must not be blank")
        return cleaned


class SalesInvoiceOut(IDTimestampMixin, SalesInvoiceBase):
    id: UUID
    status: SalesInvoiceStatus = SalesInvoiceStatus.DRAFT
    total_amount: Decimal = Decimal("0")
    posted_at: datetime | None = None
    reversed_at: datetime | None = None
    lines: list[SalesInvoiceLineOut] | None = None


class SalesInvoiceListOut(PaginatedResponse[SalesInvoiceOut]):
    pass


__all__ = [
    "SalesInvoiceLineBase",
    "SalesInvoiceLineCreate",
    "SalesInvoiceLineUpdate",
    "SalesInvoiceLineOut",
    "SalesInvoiceBase",
    "SalesInvoiceCreate",
    "SalesInvoiceUpdate",
    "SalesInvoiceOut",
    "SalesInvoiceListOut",
    "SalesInvoiceStatus",
]
