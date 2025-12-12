from __future__ import annotations

from decimal import Decimal
from typing import Any, List
from uuid import UUID
from datetime import datetime

from app.schemas.common import BaseSchema, IDTimestampMixin


class AiLogBase(BaseSchema):
    model_type: str
    input_data: str
    output_data: str | None = None
    score: Decimal | None = None


class AiLogCreate(AiLogBase):
    pass


class AiLogUpdate(BaseSchema):
    model_type: str | None = None
    input_data: str | None = None
    output_data: str | None = None
    score: Decimal | None = None


class AiLogPublic(IDTimestampMixin, AiLogBase):
    id: UUID


class AiLogList(BaseSchema):
    items: List[AiLogPublic]


class ForecastRequest(BaseSchema):
    horizon_days: int
    data: Any
    window: int | None = None
    alpha: float | None = None


class ForecastResponse(BaseSchema):
    forecast: Any
    confidence: Decimal | None = None
    intervals: dict | None = None
    baseline: list[float] | None = None
    mape: Decimal | None = None
    rmse: Decimal | None = None


class AnomalyDetectionRequest(BaseSchema):
    data: Any
    threshold: float | None = None
    method: str | None = None  # "zscore" or "iqr"
    window: int | None = None


class AnomalyDetectionResponse(BaseSchema):
    anomalies: Any
    score: Decimal | None = None
    narrative: str | None = None
    z_scores: list[float] | None = None
    threshold: float | None = None
    method: str | None = None


class AiSummaryResponse(BaseSchema):
    summary: str


class AiOverviewForecastSummary(BaseSchema):
    text: str


class AiOverviewAlert(BaseSchema):
    id: UUID
    title: str
    description: str
    created_at: datetime


class AiOverviewResponse(BaseSchema):
    anomalies_count: int
    forecast_summary: AiOverviewForecastSummary
    alerts: List[AiOverviewAlert]


__all__ = [
    "AiLogBase",
    "AiLogCreate",
    "AiLogUpdate",
    "AiLogPublic",
    "AiLogList",
    "ForecastRequest",
    "ForecastResponse",
    "AnomalyDetectionRequest",
    "AnomalyDetectionResponse",
    "AiSummaryResponse",
    "AiOverviewForecastSummary",
    "AiOverviewAlert",
    "AiOverviewResponse",
]
