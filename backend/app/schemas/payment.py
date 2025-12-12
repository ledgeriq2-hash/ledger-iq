from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID

from pydantic import field_validator

from app.schemas.common import BaseSchema, IDTimestampMixin


class PaymentBase(BaseSchema):
    invoice_id: UUID | None = None
    customer_id: UUID
    amount: Decimal
    method: str
    reference: str | None = None
    paid_at: datetime | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v is None:
            raise ValueError("amount is required")
        if Decimal(v) <= 0:
            raise ValueError("amount must be greater than zero")
        return Decimal(v)


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseSchema):
    invoice_id: UUID | None = None
    customer_id: UUID | None = None
    amount: Decimal | None = None
    method: str | None = None
    reference: str | None = None
    paid_at: datetime | None = None


class PaymentPublic(IDTimestampMixin, PaymentBase):
    id: UUID


class PaymentList(BaseSchema):
    items: List[PaymentPublic]
    page: int = 1
    page_size: int = 50
    total: int = 0
    pages: int = 0


__all__ = ["PaymentBase", "PaymentCreate", "PaymentUpdate", "PaymentPublic", "PaymentList"]
