from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema, IDTimestampMixin
from app.schemas.customer import CustomerPublic
from app.schemas.invoice import InvoiceCreate

ALLOWED_FREQUENCIES = {"daily", "weekly", "monthly", "custom"}


class RecurringInvoiceBase(BaseSchema):
    customer_id: UUID
    frequency: str = Field(description="daily|weekly|monthly|custom")
    interval: int = Field(default=1, ge=1)
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    next_run_at: datetime | None = None
    template: InvoiceCreate

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, value: str) -> str:
        value = value.lower()
        if value not in ALLOWED_FREQUENCIES:
            raise ValueError(f"frequency must be one of {', '.join(sorted(ALLOWED_FREQUENCIES))}")
        return value

    @field_validator("template")
    @classmethod
    def ensure_customer_match(cls, template: InvoiceCreate, info):
        customer_id = info.data.get("customer_id")
        if customer_id and template.customer_id != customer_id:
            raise ValueError("template.customer_id must match customer_id")
        return template


class RecurringInvoiceCreate(RecurringInvoiceBase):
    pass


class RecurringInvoiceUpdate(BaseSchema):
    customer_id: UUID | None = None
    frequency: str | None = None
    interval: int | None = Field(default=None, ge=1)
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    next_run_at: datetime | None = None
    template: InvoiceCreate | None = None

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.lower()
        if value not in ALLOWED_FREQUENCIES:
            raise ValueError(f"frequency must be one of {', '.join(sorted(ALLOWED_FREQUENCIES))}")
        return value


class RecurringInvoicePublic(IDTimestampMixin, RecurringInvoiceBase):
    id: UUID
    last_run_at: datetime | None = None
    customer: CustomerPublic | None = None


class RecurringInvoiceList(BaseSchema):
    items: list[RecurringInvoicePublic]
    page: int = 1
    page_size: int = 50
    total: int = 0
    pages: int = 0


__all__ = [
    "RecurringInvoiceCreate",
    "RecurringInvoiceUpdate",
    "RecurringInvoicePublic",
    "RecurringInvoiceList",
    "ALLOWED_FREQUENCIES",
]
