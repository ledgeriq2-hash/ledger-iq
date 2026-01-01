from __future__ import annotations

from copy import deepcopy
from typing import Any


class TenantSettingsError(RuntimeError):
    """Raised when tenant settings are missing required configuration."""


_DEFAULT_COA_MAPPING: dict[str, Any] = {
    "accounts_receivable_account_id": None,
    "revenue_account_id": None,
    "expense_account_id": None,
    "cash_account_id": None,
    "bank_account_id": None,
    "payables_account_id": None,
    "cashflow_account_ids": [],
}

_DEFAULTS = {
    "chart_of_accounts_mapping": deepcopy(_DEFAULT_COA_MAPPING),
    "limits": {},
}


def _as_dict(value: Any) -> dict:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    # Pydantic/BaseModel or ORM model with dict-like settings_json
    if hasattr(value, "model_dump"):
        try:
            dumped = value.model_dump()  # type: ignore[attr-defined]
            return dumped if isinstance(dumped, dict) else {}
        except Exception:
            return {}
    if hasattr(value, "settings_json"):
        raw = getattr(value, "settings_json", None)
        return raw if isinstance(raw, dict) else {}
    return {}


def get_tenant_settings(tenant_or_settings: Any) -> dict:
    """
    Safely obtain a tenant settings dict with defaults applied.

    - Accepts a Tenant instance or a raw settings dict.
    - Returns a fresh dict to avoid mutating ORM state inadvertently.
    - Ensures required sub-dicts exist (e.g., chart_of_accounts_mapping, limits).
    """
    base = _as_dict(tenant_or_settings)
    merged = deepcopy(_DEFAULTS)

    # merge top-level keys
    for key, value in base.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update({k: v for k, v in value.items() if v is not None})
        else:
            merged[key] = value

    # ensure chart_of_accounts_mapping has all keys
    coa = merged.setdefault("chart_of_accounts_mapping", {})
    if not isinstance(coa, dict):
        coa = {}
    for k, v in _DEFAULT_COA_MAPPING.items():
        coa.setdefault(k, v)
    merged["chart_of_accounts_mapping"] = coa

    # ensure limits present
    limits = merged.get("limits")
    if limits is None or not isinstance(limits, dict):
        merged["limits"] = {}

    return merged


__all__ = ["get_tenant_settings", "TenantSettingsError"]
