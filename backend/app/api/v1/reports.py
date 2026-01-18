from __future__ import annotations

import hashlib
import json
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.permissions import ACCOUNTANT, ADMIN, OWNER, VIEWER, require_roles
from app.models.user import User
from app.reports.pdf import export_pdf
from app.schemas.report import ReportCacheList, ReportRequest, ReportResponse
from app.accounting.use_cases.generate_client_statement import generate_client_statement
from app.accounting.use_cases.generate_party_statement import (
    generate_employee_statement,
    generate_supplier_statement,
)
from app.treasury.use_cases.generate_treasury_report import generate_treasury_report
from app.services import report_service

router = APIRouter(
    prefix="/reports",
    dependencies=[Depends(require_roles([VIEWER, ACCOUNTANT, ADMIN, OWNER]))],
)


def _hash_params(report_type: str, params: dict | None) -> str:
    payload = json.dumps({"report_type": report_type, "params": params or {}}, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _parse_date(value) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value))
    except Exception:
        return None


def _parse_uuid(value) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except Exception:
        return None


def _parse_bool(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
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


@router.get("/download/pdf")
async def download_pdf(
    report_type: str,
    from_date: date | None = None,
    to_date: date | None = None,
    as_of_date: date | None = None,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {"from_date": from_date, "to_date": to_date, "as_of_date": as_of_date}

    if report_type == "income_statement":
        data = await report_service.get_income_statement(session, tenant_id, from_date, to_date)
    elif report_type == "balance_sheet":
        data = await report_service.get_balance_sheet(session, tenant_id, as_of_date)
    elif report_type == "cashflow":
        data = await report_service.get_cashflow_statement(session, tenant_id, from_date, to_date)
    elif report_type == "trial_balance":
        data = await report_service.get_trial_balance(session, tenant_id, as_of_date)
    else:
        data = {"note": "unknown report", "params": params}

    rows = []
    if isinstance(data, dict):
        if "revenues" in data or "expenses" in data:
            rows = (data.get("revenues") or []) + (data.get("expenses") or [])
        elif "assets" in data or "liabilities" in data:
            rows = (data.get("assets") or []) + (data.get("liabilities") or []) + (data.get("equity") or [])
        elif "accounts" in data:
            rows = data.get("accounts") or []
        else:
            rows = [data]
    pdf_bytes = export_pdf(rows, title=f"{report_type} report")
    return Response(content=pdf_bytes, media_type="application/pdf")


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
    client_id_param = _parse_uuid(params.get("client_id"))
    treasury_id_param = _parse_uuid(params.get("treasury_id"))
    supplier_id_param = _parse_uuid(params.get("supplier_id"))
    employee_id_param = _parse_uuid(params.get("employee_id"))
    reference_id_param = _parse_uuid(params.get("reference_id"))
    direction_param = params.get("direction")
    reference_type_param = params.get("reference_type")
    include_zero_param = _parse_bool(params.get("include_zero"))
    include_zero = include_zero_param if include_zero_param is not None else False

    async def income_statement():
        return await report_service.get_income_statement(session, tenant_id, from_date_param, to_date_param)

    async def balance_sheet():
        return await report_service.get_balance_sheet(session, tenant_id, as_of_param)

    async def cashflow():
        return await report_service.get_cashflow_statement(session, tenant_id, from_date_param, to_date_param)

    async def trial_balance():
        if from_date_param or to_date_param:
            if not from_date_param or not to_date_param:
                return {"error": "from_date and to_date are required"}
            return await report_service.get_trial_balance_range(
                session,
                tenant_id,
                from_date=from_date_param,
                to_date=to_date_param,
                include_zero=include_zero,
            )
        if as_of_param is None:
            return {"error": "as_of_date is required"}
        return await report_service.get_trial_balance(session, tenant_id, as_of_param)

    async def client_statement():
        if not client_id_param:
            return {"error": "client_id is required"}
        return await generate_client_statement(
            session,
            tenant_id=tenant_id,
            client_id=client_id_param,
            from_date=from_date_param,
            to_date=to_date_param,
        )

    async def treasury_report():
        return await generate_treasury_report(
            session,
            tenant_id=tenant_id,
            from_date=from_date_param,
            to_date=to_date_param,
            treasury_id=treasury_id_param,
            direction=str(direction_param) if direction_param is not None else None,
            reference_type=str(reference_type_param) if reference_type_param is not None else None,
            reference_id=reference_id_param,
        )

    async def supplier_statement():
        if not supplier_id_param:
            return {"error": "supplier_id is required"}
        return await generate_supplier_statement(
            session,
            tenant_id=tenant_id,
            supplier_id=supplier_id_param,
            from_date=from_date_param,
            to_date=to_date_param,
        )

    async def employee_statement():
        if not employee_id_param:
            return {"error": "employee_id is required"}
        return await generate_employee_statement(
            session,
            tenant_id=tenant_id,
            employee_id=employee_id_param,
            from_date=from_date_param,
            to_date=to_date_param,
        )

    def fallback():
        return {"report_type": report_type, "params": params}

    if report_type == "income_statement":
        generator = income_statement
    elif report_type == "balance_sheet":
        generator = balance_sheet
    elif report_type == "cashflow":
        generator = cashflow
    elif report_type == "trial_balance":
        generator = trial_balance
    elif report_type == "client_statement":
        generator = client_statement
    elif report_type == "treasury_report":
        generator = treasury_report
    elif report_type == "supplier_statement":
        generator = supplier_statement
    elif report_type == "employee_statement":
        generator = employee_statement
    else:
        generator = fallback

    return await _run_and_cache_report(session, tenant_id, report_type, params, generator)


@router.get("/client-statement", response_model=ReportResponse)
async def client_statement(
    client_id: UUID,
    from_date: date | None = None,
    to_date: date | None = None,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {"client_id": client_id, "from_date": from_date, "to_date": to_date}

    async def generator():
        return await generate_client_statement(
            session,
            tenant_id=tenant_id,
            client_id=client_id,
            from_date=from_date,
            to_date=to_date,
        )

    return await _run_and_cache_report(session, tenant_id, "client_statement", params, generator)


@router.get("/supplier-statement", response_model=ReportResponse)
async def supplier_statement(
    supplier_id: UUID,
    from_date: date | None = None,
    to_date: date | None = None,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {"supplier_id": supplier_id, "from_date": from_date, "to_date": to_date}

    async def generator():
        return await generate_supplier_statement(
            session,
            tenant_id=tenant_id,
            supplier_id=supplier_id,
            from_date=from_date,
            to_date=to_date,
        )

    return await _run_and_cache_report(session, tenant_id, "supplier_statement", params, generator)


@router.get("/employee-statement", response_model=ReportResponse)
async def employee_statement(
    employee_id: UUID,
    from_date: date | None = None,
    to_date: date | None = None,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {"employee_id": employee_id, "from_date": from_date, "to_date": to_date}

    async def generator():
        return await generate_employee_statement(
            session,
            tenant_id=tenant_id,
            employee_id=employee_id,
            from_date=from_date,
            to_date=to_date,
        )

    return await _run_and_cache_report(session, tenant_id, "employee_statement", params, generator)


@router.get("/treasury", response_model=ReportResponse)
async def treasury_report(
    from_date: date | None = None,
    to_date: date | None = None,
    treasury_id: UUID | None = None,
    direction: str | None = None,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {
        "from_date": from_date,
        "to_date": to_date,
        "treasury_id": treasury_id,
        "direction": direction,
        "reference_type": reference_type,
        "reference_id": reference_id,
    }

    async def generator():
        return await generate_treasury_report(
            session,
            tenant_id=tenant_id,
            from_date=from_date,
            to_date=to_date,
            treasury_id=treasury_id,
            direction=direction,
            reference_type=reference_type,
            reference_id=reference_id,
        )

    return await _run_and_cache_report(session, tenant_id, "treasury_report", params, generator)


@router.get("/income-statement", response_model=ReportResponse)
async def income_statement(
    from_date: date,
    to_date: date,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {"from_date": from_date, "to_date": to_date}
    async def generator():
        return await report_service.get_income_statement(session, tenant_id, from_date, to_date)
    return await _run_and_cache_report(session, tenant_id, "income_statement", params, generator)


@router.get("/balance-sheet", response_model=ReportResponse)
async def balance_sheet(
    as_of_date: date,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {"as_of_date": as_of_date}
    async def generator():
        return await report_service.get_balance_sheet(session, tenant_id, as_of_date)
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
    async def generator():
        return await report_service.get_cashflow_statement(session, tenant_id, from_date, to_date)
    return await _run_and_cache_report(session, tenant_id, "cashflow", params, generator)


@router.get("/trial-balance", response_model=ReportResponse)
async def trial_balance(
    from_date: date | None = None,
    to_date: date | None = None,
    include_zero: bool = False,
    as_of_date: date | None = None,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    if from_date or to_date:
        if not from_date or not to_date:
            raise AppException(
                code="report_date_range_required",
                message="from_date and to_date are required",
                http_status=422,
            )
        params = {"from_date": from_date, "to_date": to_date, "include_zero": include_zero}

        async def generator():
            return await report_service.get_trial_balance_range(
                session,
                tenant_id,
                from_date=from_date,
                to_date=to_date,
                include_zero=include_zero,
            )

        return await _run_and_cache_report(session, tenant_id, "trial_balance", params, generator)

    if as_of_date is None:
        raise AppException(
            code="report_date_required",
            message="as_of_date is required",
            http_status=422,
        )

    params = {"as_of_date": as_of_date}

    async def generator():
        return await report_service.get_trial_balance(session, tenant_id, as_of_date)

    return await _run_and_cache_report(session, tenant_id, "trial_balance", params, generator)


@router.get("/general-ledger/{account_id}", response_model=ReportResponse)
async def general_ledger(
    account_id: UUID,
    from_date: date,
    to_date: date,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
):
    params = {"account_id": account_id, "from_date": from_date, "to_date": to_date}

    async def generator():
        return await report_service.get_general_ledger(
            session,
            tenant_id,
            account_id=account_id,
            from_date=from_date,
            to_date=to_date,
        )

    return await _run_and_cache_report(session, tenant_id, "general_ledger", params, generator)


__all__ = ["router"]
