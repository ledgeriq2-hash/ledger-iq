from __future__ import annotations

import asyncio
import copy
import logging
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.permissions import PERMISSION_CATALOG, ROLE_PERMISSION_PRESETS
from app.database import async_session_maker
from app.models.account import Account
from app.models.account_mapping import AccountMapping
from app.models.chart_of_account import AccountType, ChartOfAccount
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.treasury import Treasury
from app.schemas.settings import AppSettings
from app.services import billing_service
from app.services.settings_service import APP_SETTINGS_KEY, DEFAULT_PRIMARY, DEFAULT_SECONDARY

logger = logging.getLogger(__name__)

DEFAULT_ROLES = [
    {"name": role_name.upper(), "permissions_json": copy.deepcopy(permissions)}
    for role_name, permissions in ROLE_PERMISSION_PRESETS.items()
]

DEFAULT_PERMISSION_CODES = list(PERMISSION_CATALOG)

DEFAULT_ACCOUNTS = [
    {"code": "1000", "name": "Cash", "type": AccountType.ASSET},
    {"code": "1100", "name": "Accounts Receivable", "type": AccountType.ASSET},
    {"code": "2000", "name": "Accounts Payable", "type": AccountType.LIABILITY},
    {"code": "4000", "name": "Revenue", "type": AccountType.REVENUE},
    {"code": "5000", "name": "Expense", "type": AccountType.EXPENSE},
]

DEFAULT_SYSTEM_ACCOUNTS = [
    {"code": "1100", "name": "Cash", "type": "ASSET", "normal_balance": "debit"},
    {"code": "1200", "name": "Bank", "type": "ASSET", "normal_balance": "debit"},
    {"code": "1300", "name": "Accounts Receivable", "type": "ASSET", "normal_balance": "debit"},
    {"code": "2100", "name": "Accounts Payable", "type": "LIABILITY", "normal_balance": "credit"},
    {"code": "2200", "name": "Tax Payable", "type": "LIABILITY", "normal_balance": "credit"},
    {"code": "4000", "name": "Revenue", "type": "INCOME", "normal_balance": "credit"},
    {"code": "5000", "name": "Expenses", "type": "EXPENSE", "normal_balance": "debit"},
    {"code": "6100", "name": "FX Gain/Loss", "type": "INCOME", "normal_balance": "credit"},
]

DEFAULT_ACCOUNT_MAPPINGS = {
    "AR_CONTROL": "1300",
    "AP_CONTROL": "2100",
    "CASH_DEFAULT": "1100",
    "TAX_PAYABLE": "2200",
    "FX_GAIN_LOSS": "6100",
}


async def _ensure_roles(session: AsyncSession, tenant_id: UUID | None) -> list[Role]:
    result = await session.execute(select(Role).where(Role.tenant_id == tenant_id))
    existing = {role.name.upper(): role for role in result.scalars().all()}

    created: list[Role] = []
    for role_payload in DEFAULT_ROLES:
        if role_payload["name"].upper() in existing:
            continue
        role = Role(**role_payload, tenant_id=tenant_id)
        session.add(role)
        created.append(role)

    if created:
        await session.flush()

    admin_role = existing.get("ADMIN") or next((role for role in created if role.name.upper() == "ADMIN"), None)
    if admin_role:
        permissions = admin_role.permissions_json if isinstance(admin_role.permissions_json, dict) else {}
        codes = permissions.get("codes") or []
        if not isinstance(codes, list):
            codes = list(codes) if isinstance(codes, (set, tuple)) else []
        merged_codes = sorted(set(codes).union(DEFAULT_PERMISSION_CODES))
        permissions["codes"] = merged_codes
        admin_role.permissions_json = permissions

    return list(existing.values()) + created


async def _ensure_chart_of_accounts(
    session: AsyncSession, tenant_id: UUID | None
) -> list[ChartOfAccount]:
    result = await session.execute(select(ChartOfAccount).where(ChartOfAccount.tenant_id == tenant_id))
    existing = {account.code: account for account in result.scalars().all()}

    created: list[ChartOfAccount] = []
    for account_payload in DEFAULT_ACCOUNTS:
        if account_payload["code"] in existing:
            continue
        account = ChartOfAccount(**account_payload, tenant_id=tenant_id)
        session.add(account)
        created.append(account)

    if created:
        await session.flush()

    return list(existing.values()) + created


async def _ensure_system_accounts(session: AsyncSession, tenant_id: UUID | None) -> list[Account]:
    result = await session.execute(select(Account).where(Account.tenant_id == tenant_id))
    existing = {account.code: account for account in result.scalars().all()}

    created: list[Account] = []
    for payload in DEFAULT_SYSTEM_ACCOUNTS:
        if payload["code"] in existing:
            continue
        account = Account(
            tenant_id=tenant_id,
            code=payload["code"],
            name=payload["name"],
            type=payload["type"],
            normal_balance=payload["normal_balance"],
            is_system=True,
            is_active=True,
        )
        session.add(account)
        created.append(account)

    if created:
        await session.flush()

    return list(existing.values()) + created


async def _ensure_account_mappings(
    session: AsyncSession,
    tenant_id: UUID | None,
    accounts: Iterable[Account],
) -> list[AccountMapping]:
    if tenant_id is None:
        return []

    result = await session.execute(select(AccountMapping).where(AccountMapping.tenant_id == tenant_id))
    existing = {mapping.key: mapping for mapping in result.scalars().all()}
    accounts_by_code = {account.code: account for account in accounts}

    created: list[AccountMapping] = []
    for key, account_code in DEFAULT_ACCOUNT_MAPPINGS.items():
        account = accounts_by_code.get(account_code)
        if not account:
            continue
        mapping = existing.get(key)
        if mapping:
            if mapping.account_id != account.id:
                mapping.account_id = account.id
            continue
        mapping = AccountMapping(
            tenant_id=tenant_id,
            key=key,
            account_id=account.id,
        )
        session.add(mapping)
        created.append(mapping)

    if created:
        await session.flush()

    return list(existing.values()) + created


async def _ensure_default_treasury(session: AsyncSession, tenant_id: UUID | None) -> Treasury:
    result = await session.execute(select(Treasury).where(Treasury.tenant_id == tenant_id))
    treasury = result.scalars().first()
    if treasury:
        return treasury

    treasury = Treasury(type="cash", name="Cash", tenant_id=tenant_id)
    session.add(treasury)
    await session.flush()
    return treasury


def _apply_account_mapping(tenant: Tenant, accounts: Iterable[ChartOfAccount]) -> bool:
    """
    Update tenant.settings_json with default account mappings when missing.

    Primary location: settings_json["chart_of_accounts_mapping"]
    Legacy mirrors: settings_json["accounts"] and top-level keys for backward compatibility.

    Returns True when a change was applied.
    """
    account_ids = {account.name.lower(): account.id for account in accounts}
    settings = tenant.settings_json if isinstance(tenant.settings_json, dict) else {}
    chart_mapping = settings.get("chart_of_accounts_mapping")
    legacy_accounts = settings.get("accounts")
    accounts_settings: dict[str, str] = {}

    if isinstance(legacy_accounts, dict):
        accounts_settings.update({k: str(v) for k, v in legacy_accounts.items() if v is not None})
    if isinstance(chart_mapping, dict):
        accounts_settings.update({k: str(v) for k, v in chart_mapping.items() if v is not None})
    needs_sync = not isinstance(chart_mapping, dict) and bool(accounts_settings)

    changes = 0

    def _set_if_missing(container: dict, key: str, value: UUID | None) -> None:
        nonlocal changes
        if value and container.get(key) is None:
            container[key] = str(value)
            changes += 1

    _set_if_missing(accounts_settings, "cash_account_id", account_ids.get("cash"))
    _set_if_missing(
        accounts_settings,
        "accounts_receivable_account_id",
        account_ids.get("accounts receivable"),
    )
    _set_if_missing(accounts_settings, "payables_account_id", account_ids.get("accounts payable"))
    _set_if_missing(accounts_settings, "revenue_account_id", account_ids.get("revenue"))
    _set_if_missing(accounts_settings, "expense_account_id", account_ids.get("expense"))
    if accounts_settings.get("cashflow_account_ids") is None and accounts_settings.get("cash_account_id") is not None:
        accounts_settings["cashflow_account_ids"] = [accounts_settings["cash_account_id"]]
        changes += 1

    # mirror top-level keys for backwards compatibility with earlier settings lookups
    for key, value in list(accounts_settings.items()):
        if key == "cashflow_account_ids":
            if isinstance(settings.get(key), list):
                continue
            settings[key] = value
            changes += 1
            continue
        _set_if_missing(settings, key, UUID(value))

    if changes or needs_sync:
        settings["chart_of_accounts_mapping"] = accounts_settings
        settings["accounts"] = accounts_settings
        tenant.settings_json = settings
        return True
    return False


def _apply_app_settings_defaults(tenant: Tenant) -> bool:
    """
    Ensure tenant.settings_json["app_settings"] exists with stable defaults.

    This prevents missing feature toggles / settings on a fresh DB.
    """
    root = tenant.settings_json if isinstance(tenant.settings_json, dict) else {}
    existing = root.get(APP_SETTINGS_KEY)
    if isinstance(existing, dict) and existing:
        return False

    defaults = AppSettings(
        feature_toggles={
            "ai": True,
            "suppliers": True,
            "workers": True,
            "debts": True,
            "invoices": True,
            "pages": {
                "dashboard_ai": True,
                "dashboard_suppliers": True,
                "dashboard_workers": True,
                "dashboard_debts": True,
                "dashboard_invoices": True,
            },
        },
        currency="USD",
        taxes={"enabled": False, "rate": 0},
        field_labels={},
        theme={"primary": DEFAULT_PRIMARY, "secondary": DEFAULT_SECONDARY, "mode": "light"},
    ).model_dump()

    root[APP_SETTINGS_KEY] = defaults
    tenant.settings_json = root
    return True


async def seed_tenant(session: AsyncSession, tenant: Tenant | None) -> None:
    tenant_id = tenant.id if tenant else None
    roles = await _ensure_roles(session, tenant_id)
    chart_accounts = await _ensure_chart_of_accounts(session, tenant_id)
    system_accounts = await _ensure_system_accounts(session, tenant_id)
    account_mappings = await _ensure_account_mappings(session, tenant_id, system_accounts)
    treasury = await _ensure_default_treasury(session, tenant_id)
    mapping_changed = bool(tenant and _apply_account_mapping(tenant, chart_accounts))
    settings_changed = bool(tenant and _apply_app_settings_defaults(tenant))
    if roles or chart_accounts or system_accounts or account_mappings or mapping_changed or settings_changed or treasury:
        await session.commit()
        for entity in roles + chart_accounts + system_accounts + account_mappings:
            await session.refresh(entity)
        await session.refresh(treasury)
        if mapping_changed and tenant:
            await session.refresh(tenant)
        if settings_changed and tenant:
            await session.refresh(tenant)

    if roles:
        logger.info("Ensured %s roles for tenant %s", len(roles), tenant_id or "GLOBAL")
    if chart_accounts:
        logger.info("Ensured %s chart accounts for tenant %s", len(chart_accounts), tenant_id or "GLOBAL")
    if system_accounts:
        logger.info("Ensured %s system accounts for tenant %s", len(system_accounts), tenant_id or "GLOBAL")
    if account_mappings:
        logger.info("Ensured %s account mappings for tenant %s", len(account_mappings), tenant_id or "GLOBAL")
    if mapping_changed and tenant:
        logger.info("Updated account mappings for tenant %s", tenant.slug)
    if settings_changed and tenant:
        logger.info("Ensured app_settings defaults for tenant %s", tenant.slug)
    if treasury:
        logger.info("Ensured default treasury for tenant %s", tenant_id or "GLOBAL")


async def seed_all() -> None:
    settings = get_settings()
    logger.info("Seeding defaults using database %s", settings.database_url)

    async with async_session_maker() as session:
        await billing_service.ensure_default_plans(session, settings)
        result = await session.execute(select(Tenant))
        tenants = result.scalars().all()

        if not tenants:
            logger.info("No tenants found; seeding global defaults (tenant_id=None)")
            await seed_tenant(session, None)
        else:
            for tenant in tenants:
                await seed_tenant(session, tenant)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_all())


if __name__ == "__main__":
    main()
