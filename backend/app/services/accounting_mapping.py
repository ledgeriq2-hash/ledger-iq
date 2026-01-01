from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.settings_utils import get_tenant_settings
from app.models.tenant import Tenant


@dataclass(frozen=True, slots=True)
class AccountMappingRequirement:
    required_all: tuple[str, ...] = ()
    required_any: tuple[tuple[str, ...], ...] = ()
    context: str | None = None


_CASH_OR_BANK_GROUP = ("cashflow_account_ids", "cash_account_id", "bank_account_id")

ACCOUNT_MAPPING_REQUIREMENTS: dict[str, AccountMappingRequirement] = {
    "invoice_posting": AccountMappingRequirement(
        required_all=("accounts_receivable_account_id", "revenue_account_id"),
        context="invoice_posting",
    ),
    "payment_receipt": AccountMappingRequirement(
        required_all=("accounts_receivable_account_id",),
        required_any=(_CASH_OR_BANK_GROUP,),
        context="payment_receipt",
    ),
    "supplier_expense": AccountMappingRequirement(
        required_all=("expense_account_id",),
        required_any=(("payables_account_id",), _CASH_OR_BANK_GROUP),
        context="supplier_expense",
    ),
    "payment_adjustment": AccountMappingRequirement(
        required_all=("expense_account_id", "payables_account_id"),
        context="payment_adjustment",
    ),
    "treasury_movement": AccountMappingRequirement(
        required_any=(_CASH_OR_BANK_GROUP,),
        context="treasury_movement",
    ),
    "treasury_receipt": AccountMappingRequirement(
        required_all=("accounts_receivable_account_id",),
        required_any=(_CASH_OR_BANK_GROUP,),
        context="treasury_receipt",
    ),
    "treasury_supplier_payment": AccountMappingRequirement(
        required_all=("payables_account_id",),
        required_any=(_CASH_OR_BANK_GROUP,),
        context="treasury_supplier_payment",
    ),
    "treasury_expense": AccountMappingRequirement(
        required_all=("expense_account_id",),
        required_any=(_CASH_OR_BANK_GROUP,),
        context="treasury_expense",
    ),
    "treasury_payroll_payout": AccountMappingRequirement(
        required_all=("expense_account_id",),
        required_any=(_CASH_OR_BANK_GROUP,),
        context="treasury_payroll_payout",
    ),
    "treasury_employee_payment": AccountMappingRequirement(
        required_all=("expense_account_id",),
        required_any=(_CASH_OR_BANK_GROUP,),
        context="treasury_employee_payment",
    ),
    "treasury_disbursement": AccountMappingRequirement(
        required_any=(_CASH_OR_BANK_GROUP,),
        context="treasury_disbursement",
    ),
}


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


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, Iterable) and not isinstance(value, (dict, bytes, bytearray, str)):
        return len(list(value)) == 0
    return False


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

def _missing_required_keys(mapping: dict[str, Any], requirement: AccountMappingRequirement) -> tuple[list[str], list[list[str]]]:
    missing_all = [key for key in requirement.required_all if _is_missing(mapping.get(key))]
    missing_any: list[list[str]] = []
    for group in requirement.required_any:
        if not any(not _is_missing(mapping.get(key)) for key in group):
            missing_any.append(list(group))
    return missing_all, missing_any


async def validate_tenant_account_mapping(
    session: AsyncSession,
    tenant_id: UUID,
    requirement: AccountMappingRequirement,
) -> dict[str, Any]:
    mapping = await get_account_mapping(session, tenant_id)
    missing_all, missing_any = _missing_required_keys(mapping, requirement)
    if missing_all or missing_any:
        raise AppException(
            code="account_mapping_missing",
            message="Account mapping is missing required keys",
            details={
                "context": requirement.context,
                "missing_all": missing_all,
                "missing_any": missing_any,
                "required_all": list(requirement.required_all),
                "required_any": [list(group) for group in requirement.required_any],
            },
            http_status=422,
        )
    return mapping


__all__ = ["get_account_mapping", "validate_tenant_account_mapping", "AccountMappingRequirement", "ACCOUNT_MAPPING_REQUIREMENTS"]
