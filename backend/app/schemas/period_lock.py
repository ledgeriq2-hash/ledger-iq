from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from app.schemas.common import BaseSchema, IDTimestampMixin


class AccountingPeriodLockCreate(BaseSchema):
    start_date: date
    end_date: date


class AccountingPeriodLockPublic(IDTimestampMixin):
    start_date: date
    end_date: date
    locked_at: datetime
    locked_by: UUID | None = None


__all__ = ["AccountingPeriodLockCreate", "AccountingPeriodLockPublic"]
