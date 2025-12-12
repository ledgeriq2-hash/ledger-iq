from __future__ import annotations

from datetime import datetime
from typing import Any, List
from uuid import UUID

from app.schemas.common import BaseSchema, IDTimestampMixin


class ReportCacheBase(BaseSchema):
    report_type: str
    params_hash: str
    data_json: str
    expires_at: datetime | None = None


class ReportCacheCreate(ReportCacheBase):
    pass


class ReportCacheUpdate(BaseSchema):
    report_type: str | None = None
    params_hash: str | None = None
    data_json: str | None = None
    expires_at: datetime | None = None


class ReportCachePublic(IDTimestampMixin, ReportCacheBase):
    id: UUID


class ReportCacheList(BaseSchema):
    items: List[ReportCachePublic]


class ReportRequest(BaseSchema):
    report_type: str
    params: dict[str, Any] | None = None


class ReportResponse(BaseSchema):
    report_type: str
    data: Any


__all__ = [
    "ReportCacheBase",
    "ReportCacheCreate",
    "ReportCacheUpdate",
    "ReportCachePublic",
    "ReportCacheList",
    "ReportRequest",
    "ReportResponse",
]
