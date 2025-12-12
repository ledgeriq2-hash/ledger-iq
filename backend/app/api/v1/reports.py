from __future__ import annotations

import hashlib
import json
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.schemas.report import ReportCacheList, ReportRequest, ReportResponse
from app.services import report_service

router = APIRouter(
    prefix="/reports",
    dependencies=[Depends(require_roles([VIEWER, ACCOUNTANT, ADMIN, OWNER]))],
)


def _hash_params(report_type: str, params: dict | None) -> str:
    payload = json.dumps({"report_type": report_type, "params": params or {}}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _parse_date(value) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value))
    except Exception:
        return None


async def _run_and_cache_report(
    session: AsyncSession,
    tenant_id: UUID,
    report_type: str,
    params: dict | None,
    generator,
) -> ReportResponse:
    params_hash = _hash_params(report_type, params or {})
    result = await report_service.get_report_data(
        session,
        tenant_id,
        report_type,
        params_hash,
        generator=generator,
    )
    return ReportResponse(report_type=result["report_type"], data=result["data"])


@router.get("/cache", response_model=ReportCacheList)
async def list_cache(
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    caches = await report_service.list_report_cache(session, tenant_id)
    return ReportCacheList(items=caches)


@router.post("/run", response_model=ReportResponse)
async def run_report(
    payload: ReportRequest,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = payload.params or {}
    report_type = payload.report_type
    from_date_param = _parse_date(params.get("from_date"))
    to_date_param = _parse_date(params.get("to_date"))
    as_of_param = _parse_date(params.get("as_of_date"))

    if report_type == "income_statement":
        generator = lambda: report_service.get_income_statement(session, tenant_id, from_date_param, to_date_param)
    elif report_type == "balance_sheet":
        generator = lambda: report_service.get_balance_sheet(session, tenant_id, as_of_param)
    elif report_type == "cashflow":
        generator = lambda: report_service.get_cashflow_statement(session, tenant_id, from_date_param, to_date_param)
    elif report_type == "trial_balance":
        generator = lambda: report_service.get_trial_balance(session, tenant_id, as_of_param)
    else:
        generator = lambda: {"report_type": report_type, "params": params}

    return await _run_and_cache_report(session, tenant_id, report_type, params, generator)


@router.get("/income-statement", response_model=ReportResponse)
async def income_statement(
    from_date: date,
    to_date: date,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {"from_date": from_date, "to_date": to_date}
    generator = lambda: report_service.get_income_statement(session, tenant_id, from_date, to_date)
    return await _run_and_cache_report(session, tenant_id, "income_statement", params, generator)


@router.get("/balance-sheet", response_model=ReportResponse)
async def balance_sheet(
    as_of_date: date,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {"as_of_date": as_of_date}
    generator = lambda: report_service.get_balance_sheet(session, tenant_id, as_of_date)
    return await _run_and_cache_report(session, tenant_id, "balance_sheet", params, generator)


@router.get("/cashflow", response_model=ReportResponse)
async def cashflow_statement(
    from_date: date,
    to_date: date,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {"from_date": from_date, "to_date": to_date}
    generator = lambda: report_service.get_cashflow_statement(session, tenant_id, from_date, to_date)
    return await _run_and_cache_report(session, tenant_id, "cashflow", params, generator)


@router.get("/trial-balance", response_model=ReportResponse)
async def trial_balance(
    as_of_date: date,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {"as_of_date": as_of_date}
    generator = lambda: report_service.get_trial_balance(session, tenant_id, as_of_date)
    return await _run_and_cache_report(session, tenant_id, "trial_balance", params, generator)


__all__ = ["router"]
