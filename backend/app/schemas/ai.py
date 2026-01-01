from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from app.schemas.common import BaseSchema, IDTimestampMixin
from pydantic import Field


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
    items: list[AiLogPublic]


class AiDatasetPoint(BaseSchema):
    label: str | None = None
    period: str | None = None
    value: float


class AiDatasetMetadata(BaseSchema):
    filters: dict[str, Any] = Field(default_factory=dict)
    window: int | None = None
    horizon_days: int | None = None
    alpha: float | None = None
    granularity: str | None = None


class AiDatasetV1(BaseSchema):
    schema_version: Literal["ai-dataset-v1"]
    points: list[AiDatasetPoint]
    metadata: AiDatasetMetadata | None = None


class ForecastRequest(BaseSchema):
    horizon_days: int
    data: Any
    dataset: AiDatasetV1 | None = None
    window: int | None = None
    alpha: float | None = None


class ForecastResponse(BaseSchema):
    forecast: Any
    confidence: Decimal | None = None
    intervals: dict | None = None
    baseline: list[float] | None = None
    mape: Decimal | None = None
    rmse: Decimal | None = None
    model_version: str | None = None
    run_id: UUID | None = None


class AnomalyDetectionRequest(BaseSchema):
    data: Any
    dataset: AiDatasetV1 | None = None
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
    alerts: list[AiOverviewAlert]


class AiRunPublic(IDTimestampMixin, BaseSchema):
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    error: str | None = None


class AiInsightPublic(IDTimestampMixin, BaseSchema):
    run_id: UUID
    type: str
    severity: str
    confidence: Decimal
    title: str
    message: str
    explanation: str | None = None
    reference_type: str | None = None
    reference_id: UUID | None = None


class AiInsightsSummaryResponse(BaseSchema):
    insights: list[AiInsightPublic]


class AiInsightsListResponse(BaseSchema):
    insights: list[AiInsightPublic]
    filters: dict[str, Any] | None = None


class AiRunResponse(BaseSchema):
    run: AiRunPublic
    insights: list[AiInsightPublic]


class AiRunList(BaseSchema):
    items: list[AiRunPublic]


class AiInsightsQuery(BaseSchema):
    from_date: date | None = None
    to_date: date | None = None
    severity: str | None = None
    min_confidence: Decimal | None = None
    type: str | None = None


__all__ = [
    "AiLogBase",
    "AiLogCreate",
    "AiLogUpdate",
    "AiLogPublic",
    "AiLogList",
    "AiDatasetPoint",
    "AiDatasetMetadata",
    "AiDatasetV1",
    "ForecastRequest",
    "ForecastResponse",
    "AnomalyDetectionRequest",
    "AnomalyDetectionResponse",
    "AiSummaryResponse",
    "AiOverviewForecastSummary",
    "AiOverviewAlert",
    "AiOverviewResponse",
    "AiRunPublic",
    "AiInsightPublic",
    "AiInsightsSummaryResponse",
    "AiInsightsListResponse",
    "AiRunResponse",
    "AiRunList",
    "AiInsightsQuery",
]
