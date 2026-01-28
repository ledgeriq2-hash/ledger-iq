from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import field_validator

from app.core.pagination import PaginatedResponse
from app.models.fx_revaluation_run import FXRevaluationStatus
from app.schemas.common import BaseSchema, IDTimestampMixin


class FXRevaluationRunCreate(BaseSchema):
    period_id: str
    currency: str
    reval_fx_rate: Decimal

    @field_validator("currency")
    @classmethod
    def currency_not_blank(cls, value: str) -> str:
        cleaned = (value or "").strip().upper()
        if not cleaned:
            raise ValueError("currency is required")
        return cleaned

    @field_validator("reval_fx_rate")
    @classmethod
    def fx_rate_positive(cls, value: Decimal) -> Decimal:
        if Decimal(str(value)) <= 0:
            raise ValueError("reval_fx_rate must be greater than zero")
        return value


class FXRevaluationLineRead(IDTimestampMixin):
    id: UUID
    source_type: str
    source_id: UUID
    foreign_remaining: Decimal
    old_base_remaining: Decimal
    new_base_remaining: Decimal
    delta_base: Decimal


class FXRevaluationRunRead(IDTimestampMixin):
    id: UUID
    period_year: int
    period_month: int
    currency_code: str
    reval_fx_rate: Decimal
    status: FXRevaluationStatus = FXRevaluationStatus.POSTED
    posting_journal_entry_id: UUID | None = None
    reversed_at: datetime | None = None
    lines: list[FXRevaluationLineRead] | None = None


class FXRevaluationRunList(PaginatedResponse[FXRevaluationRunRead]):
    pass


__all__ = [
    "FXRevaluationRunCreate",
    "FXRevaluationRunRead",
    "FXRevaluationRunList",
    "FXRevaluationLineRead",
    "FXRevaluationStatus",
]
