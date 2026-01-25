from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.models.user import User
from app.schemas.ai import (
    AiLogList,
    AiLogPublic,
    AiOverviewResponse,
    AiInsightPublic,
    AiInsightsListResponse,
    AiInsightsSummaryResponse,
    AiRunList,
    AiSummaryResponse,
    AiRunPublic,
    AiRunResponse,
    AnomalyDetectionRequest,
    AnomalyDetectionResponse,
    ForecastRequest,
    ForecastResponse,
)
from app.services import ai_service
from app.services import ai_insights_service

router = APIRouter(prefix="/ai")


@router.get("/logs", response_model=AiLogList)
async def list_logs(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    logs = await ai_service.list_ai_logs(session, tenant_id)
    return AiLogList(items=logs)


@router.get("/logs/{log_id}", response_model=AiLogPublic)
async def get_log(
    log_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    log = await ai_service.get_ai_log(session, tenant_id, log_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
    return log


@router.delete("/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_log(
    log_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    deleted = await ai_service.delete_ai_log(session, tenant_id, log_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
    return None


@router.post("/forecast", response_model=ForecastResponse)
async def forecast(
    payload: ForecastRequest,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    actor: User = Depends(deps.get_current_active_user),
):
    result = await ai_service.run_forecast(session, tenant_id, payload, requested_by=actor.id)
    return ForecastResponse(**result)


@router.post("/anomaly", response_model=AnomalyDetectionResponse)
async def anomaly(
    payload: AnomalyDetectionRequest,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    result = await ai_service.run_anomaly_detection(session, tenant_id, payload)
    return AnomalyDetectionResponse(**result)


@router.post("/summary", response_model=AiSummaryResponse)
async def reports_summary(
    payload: dict,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    result = await ai_service.summarize_reports(session, tenant_id, payload)
    return AiSummaryResponse(**result)


@router.get("/summary", response_model=AiInsightsSummaryResponse)
async def top_insights(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    insights = await ai_insights_service.get_top_insights(session, tenant_id=tenant_id, limit=3)
    return AiInsightsSummaryResponse(insights=[AiInsightPublic.model_validate(i) for i in insights])


@router.get("/insights", response_model=AiInsightsListResponse)
async def list_insights(
    from_date: date | None = None,
    to_date: date | None = None,
    severity: str | None = None,
    min_confidence: Decimal | None = None,
    type: str | None = None,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    insights = await ai_insights_service.list_insights(
        session,
        tenant_id=tenant_id,
        from_date=from_date,
        to_date=to_date,
        severity=severity,
        min_confidence=min_confidence,
        type=type,
        limit=200,
    )
    filters = {
        "from_date": from_date,
        "to_date": to_date,
        "severity": severity,
        "min_confidence": min_confidence,
        "type": type,
    }
    return AiInsightsListResponse(
        insights=[AiInsightPublic.model_validate(i) for i in insights],
        filters=filters,
    )


@router.post("/run", response_model=AiRunResponse)
async def run_ai(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    run, insights = await ai_insights_service.run_ai(session, tenant_id=tenant_id)
    return AiRunResponse(
        run=AiRunPublic.model_validate(run),
        insights=[AiInsightPublic.model_validate(i) for i in insights],
    )


@router.get("/overview", response_model=AiOverviewResponse)
async def overview(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    return await ai_service.get_ai_overview(session, tenant_id)


@router.get("/legacy-runs", response_model=AiRunList)
async def list_runs(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    runs = await ai_insights_service.list_runs(session, tenant_id=tenant_id, limit=200)
    return AiRunList(items=[AiRunPublic.model_validate(r) for r in runs])


__all__ = ["router"]
