from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import anomaly, forecast
from app.metrics import ADMIN_ACTIONS, AI_FORECASTS_CALLED, AI_USAGE, ANOMALIES_DETECTED
from app.models.ai_log import AiLog
from app.models.ai_run import AiRun
from app.schemas.ai import (
    AiOverviewAlert,
    AiOverviewForecastSummary,
    AiOverviewResponse,
)
from app.services import billing_service


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _json_dumps(value: Any) -> str:
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except TypeError:
        return str(value)


def _jsonable(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))
    except Exception:
        return str(value)


async def list_ai_logs(session: AsyncSession, tenant_id: UUID) -> Sequence[AiLog]:
    result = await session.execute(select(AiLog).where(AiLog.tenant_id == tenant_id))
    return result.scalars().all()


async def get_ai_log(session: AsyncSession, tenant_id: UUID, log_id: UUID) -> AiLog | None:
    result = await session.execute(select(AiLog).where(AiLog.id == log_id, AiLog.tenant_id == tenant_id))
    return result.scalar_one_or_none()


async def create_ai_log(session: AsyncSession, tenant_id: UUID, payload: Any) -> AiLog:
    data = _to_dict(payload)
    log = AiLog(**data, tenant_id=tenant_id)
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def delete_ai_log(session: AsyncSession, tenant_id: UUID, log_id: UUID) -> bool:
    result = await session.execute(delete(AiLog).where(AiLog.id == log_id, AiLog.tenant_id == tenant_id))
    await session.commit()
    return result.rowcount > 0


def _call_ai_function(module: Any, function_names: list[str], *args: Any, **kwargs: Any) -> Any:
    for name in function_names:
        func = getattr(module, name, None)
        if callable(func):
            return func(*args, **kwargs)
    raise RuntimeError(f"No AI function found in module {module.__name__} for names {function_names}")


async def run_forecast(
    session: AsyncSession,
    tenant_id: UUID,
    request: Any,
    *,
    requested_by: UUID | None = None,
) -> dict[str, Any]:
    await billing_service.enforce_plan_limit(session, tenant_id, "ai_calls")
    data = _to_dict(request)
    started_at = datetime.now(UTC)
    run = AiRun(
        tenant_id=tenant_id,
        status="RUNNING",
        started_at=started_at,
        finished_at=None,
        error=None,
        prediction_type="forecast",
        model_version="forecast-v1",
        data_snapshot_id=None,
        params={"request": _jsonable(data)},
        metrics={},
        trigger="forecast",
        requested_by=requested_by,
    )
    session.add(run)
    await session.flush()

    result: Any | None = None
    error: str | None = None
    try:
        result = _call_ai_function(forecast, ["generate_forecast", "run_forecast"], data)
    except Exception as exc:
        error = str(exc)[:500]
        result = None

    score = None
    if isinstance(result, dict):
        score = result.get("confidence")
    payload_bytes = len(_json_dumps(data).encode("utf-8"))
    result_bytes = len(_json_dumps(result).encode("utf-8")) if result is not None else 0
    increment_mb = (payload_bytes + result_bytes) / (1024 * 1024)
    await billing_service.enforce_plan_limit(session, tenant_id, "storage_mb", increment=increment_mb)

    metrics: dict[str, Any] = {}
    if isinstance(result, dict):
        for key in ("confidence", "mape", "rmse"):
            if key in result:
                metrics[key] = _jsonable(result.get(key))
    if error:
        run.status = "FAILED"
        run.error = error
    else:
        run.status = "SUCCESS"
    run.finished_at = datetime.now(UTC)
    run.metrics = metrics
    await session.commit()
    await session.refresh(run)

    log = await create_ai_log(
        session,
        tenant_id,
        {
            "model_type": "forecast",
            "input_data": _json_dumps(data),
            "output_data": _json_dumps(result),
            "score": Decimal(str(score)) if score is not None else None,
        },
    )
    try:
        ADMIN_ACTIONS.labels(action="ai_forecast").inc()
        AI_USAGE.labels(tenant_id=str(tenant_id), action="forecast").inc()
        AI_FORECASTS_CALLED.labels(tenant_id=str(tenant_id)).inc()
    except Exception:
        pass
    return {
        "forecast": result.get("forecast") if isinstance(result, dict) else result,
        "confidence": score,
        "intervals": result.get("intervals") if isinstance(result, dict) else None,
        "baseline": result.get("baseline") if isinstance(result, dict) else None,
        "mape": result.get("mape") if isinstance(result, dict) else None,
        "rmse": result.get("rmse") if isinstance(result, dict) else None,
        "model_version": "forecast-v1",
        "run_id": run.id,
    }


def _anomaly_count(result: Any) -> int:
    if isinstance(result, dict):
        anomalies = result.get("anomalies")
        if isinstance(anomalies, Sequence) and not isinstance(anomalies, (str, bytes, bytearray)):
            return len(anomalies)
    if isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
        return len(result)
    return 1


async def run_anomaly_detection(session: AsyncSession, tenant_id: UUID, request: Any) -> dict[str, Any]:
    await billing_service.enforce_plan_limit(session, tenant_id, "ai_calls")
    data = _to_dict(request)
    result: Any | None = None
    try:
        result = _call_ai_function(anomaly, ["detect_anomalies", "run_anomaly_detection"], data)
    except Exception:
        result = None

    score = None
    if isinstance(result, dict):
        score = result.get("score")
    payload_bytes = len(_json_dumps(data).encode("utf-8"))
    result_bytes = len(_json_dumps(result).encode("utf-8")) if result is not None else 0
    increment_mb = (payload_bytes + result_bytes) / (1024 * 1024)
    await billing_service.enforce_plan_limit(session, tenant_id, "storage_mb", increment=increment_mb)

    await create_ai_log(
        session,
        tenant_id,
        {
            "model_type": "anomaly",
            "input_data": _json_dumps(data),
            "output_data": _json_dumps(result),
            "score": Decimal(str(score)) if score is not None else None,
        },
    )
    anomaly_count = _anomaly_count(result)
    try:
        ADMIN_ACTIONS.labels(action="ai_anomaly").inc()
        AI_USAGE.labels(tenant_id=str(tenant_id), action="anomaly").inc()
        ANOMALIES_DETECTED.labels(tenant_id=str(tenant_id)).inc(anomaly_count)
    except Exception:
        pass
    return {
        "anomalies": result.get("anomalies") if isinstance(result, dict) else result,
        "score": score,
        "narrative": result.get("narrative") if isinstance(result, dict) else None,
    }


async def summarize_reports(session: AsyncSession, tenant_id: UUID, payload: Any) -> dict[str, Any]:
    """
    Generate a lightweight narrative summary for balance sheet and income statement.
    """
    data = _to_dict(payload)
    balance = data.get("balance_sheet") or {}
    income = data.get("income_statement") or {}
    summary_lines: list[str] = []

    cash = balance.get("cash") or balance.get("cash_and_equivalents")
    if cash is not None:
        summary_lines.append(f"Cash position: {cash}.")
    revenue = income.get("revenue") or income.get("total_revenue")
    net_income = income.get("net_income") or income.get("profit")
    if revenue is not None:
        summary_lines.append(f"Revenue: {revenue}.")
    if net_income is not None:
        summary_lines.append(f"Net income: {net_income}.")

    summary = " ".join(summary_lines) or "Reports not populated yet."
    try:
        ADMIN_ACTIONS.labels(action="ai_reports_summary").inc()
        AI_USAGE.labels(tenant_id=str(tenant_id), action="reports_summary").inc()
    except Exception:
        pass
    await billing_service.enforce_plan_limit(session, tenant_id, "ai_calls")
    return {"summary": summary}


async def _count_recent_anomalies(
    session: AsyncSession, tenant_id: UUID, since: datetime
) -> int:
    result = await session.execute(
        select(func.count()).where(
            AiLog.tenant_id == tenant_id,
            AiLog.model_type == "anomaly",
            AiLog.created_at >= since,
        )
    )
    return int(result.scalar_one() or 0)


async def _get_latest_forecast_log(session: AsyncSession, tenant_id: UUID) -> AiLog | None:
    result = await session.execute(
        select(AiLog)
        .where(AiLog.tenant_id == tenant_id, AiLog.model_type == "forecast")
        .order_by(AiLog.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _summarize_forecast_log(log: AiLog | None) -> str:
    if not log or not log.output_data:
        return "Forecast data is not available yet."
    try:
        parsed = json.loads(log.output_data)
    except Exception:
        return log.output_data[:200]
    if isinstance(parsed, dict):
        summary = parsed.get("summary")
        if summary:
            return str(summary)
        notes: list[str] = []
        forecast_values = parsed.get("forecast")
        if isinstance(forecast_values, Sequence):
            notes.append(f"Forecast generated for {len(forecast_values)} points.")
        confidence = parsed.get("confidence")
        if confidence is not None:
            notes.append(f"Confidence {confidence}.")
        return " ".join(notes) or "Forecast data recorded."
    return str(parsed)


def _alert_description(log: AiLog) -> str:
    if not log.output_data:
        return "No additional details."
    try:
        parsed = json.loads(log.output_data)
    except Exception:
        return log.output_data[:200]
    if isinstance(parsed, dict):
        for key in ("summary", "message", "description"):
            value = parsed.get(key)
            if value:
                return str(value)
        return json.dumps(parsed)[:200]
    return str(parsed)


async def _collect_ai_alerts(session: AsyncSession, tenant_id: UUID, limit: int = 5) -> list[AiOverviewAlert]:
    result = await session.execute(
        select(AiLog)
        .where(AiLog.tenant_id == tenant_id)
        .order_by(AiLog.created_at.desc())
        .limit(limit)
    )
    alerts = []
    for log in result.scalars().all():
        alerts.append(
            AiOverviewAlert(
                id=log.id,
                title=f"{(log.model_type or 'AI').title()} alert",
                description=_alert_description(log),
                created_at=log.created_at,
            )
        )
    return alerts


async def get_ai_overview(session: AsyncSession, tenant_id: UUID) -> AiOverviewResponse:
    now = datetime.now(UTC)
    since = now - timedelta(days=30)
    anomalies_count = await _count_recent_anomalies(session, tenant_id, since)
    forecast_summary = _summarize_forecast_log(await _get_latest_forecast_log(session, tenant_id))
    alerts = await _collect_ai_alerts(session, tenant_id)
    return AiOverviewResponse(
        anomalies_count=anomalies_count,
        forecast_summary=AiOverviewForecastSummary(text=forecast_summary),
        alerts=alerts,
    )


__all__ = [
    "list_ai_logs",
    "get_ai_log",
    "create_ai_log",
    "delete_ai_log",
    "run_forecast",
    "run_anomaly_detection",
    "summarize_reports",
    "get_ai_overview",
]
