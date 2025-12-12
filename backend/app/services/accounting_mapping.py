from __future__ import annotations

from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings_utils import get_tenant_settings
from app.models.tenant import Tenant


def _parse_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except Exception:
        return None


def _parse_uuid_list(values: Any) -> list[UUID]:
    if values is None:
        return []
    parsed: list[UUID] = []
    if isinstance(values, (list, tuple, set)):
        for val in values:
            candidate = _parse_uuid(val)
            if candidate:
                parsed.append(candidate)
    else:
        candidate = _parse_uuid(values)
        if candidate:
            parsed.append(candidate)
    return parsed


def _pick(mapping: dict, accounts: dict, settings: dict, *keys: str) -> Any:
    for key in keys:
        for source in (mapping, accounts, settings):
            if isinstance(source, dict) and source.get(key) is not None:
                return source[key]
    return None


async def get_account_mapping(session: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    result = await session.execute(select(Tenant.settings_json).where(Tenant.id == tenant_id))
    raw_settings = result.scalar_one_or_none() or {}
    settings = get_tenant_settings(raw_settings)
    mapping = settings.get("chart_of_accounts_mapping") or {}
    accounts = settings.get("accounts") if isinstance(settings.get("accounts"), dict) else {}

    ar_id = _parse_uuid(
        _pick(
            mapping,
            accounts,
            settings,
            "accounts_receivable_account_id",
            "accounts_receivable",
            "accounts_receivable_account",
        )
    )
    revenue_id = _parse_uuid(_pick(mapping, accounts, settings, "revenue_account_id", "revenue_account"))
    cash_id = _parse_uuid(
        _pick(
            mapping,
            accounts,
            settings,
            "cash_account_id",
            "bank_account_id",
            "cash_and_bank_account_id",
        )
    )
    payables_id = _parse_uuid(_pick(mapping, accounts, settings, "payables_account_id", "accounts_payable_account_id"))
    expense_id = _parse_uuid(_pick(mapping, accounts, settings, "expense_account_id", "expenses_account_id"))
    cashflow_ids = _parse_uuid_list(
        _pick(mapping, accounts, settings, "cashflow_account_ids", "cash_account_ids", "bank_account_ids")
    )
    if not cashflow_ids and cash_id:
        cashflow_ids = [cash_id]

    return {
        "accounts_receivable_account_id": ar_id,
        "revenue_account_id": revenue_id,
        "cash_account_id": cash_id,
        "payables_account_id": payables_id,
        "expense_account_id": expense_id,
        "cashflow_account_ids": cashflow_ids,
    }


__all__ = ["get_account_mapping"]
