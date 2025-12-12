from __future__ import annotations

import asyncio
import logging
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import async_session_maker
from app.models.chart_of_account import AccountType, ChartOfAccount
from app.models.role import Role
from app.models.tenant import Tenant
from app.services import billing_service

logger = logging.getLogger(__name__)

DEFAULT_ROLES = [
    {"name": "OWNER", "permissions_json": {"all": True}},
    {"name": "ADMIN", "permissions_json": {"all": True}},
    {"name": "ACCOUNTANT", "permissions_json": {"accounting": True}},
    {"name": "VIEWER", "permissions_json": {"read_only": True}},
]

DEFAULT_ACCOUNTS = [
    {"code": "1000", "name": "Cash", "type": AccountType.ASSET},
    {"code": "1100", "name": "Accounts Receivable", "type": AccountType.ASSET},
    {"code": "4000", "name": "Revenue", "type": AccountType.REVENUE},
    {"code": "5000", "name": "Expense", "type": AccountType.EXPENSE},
]


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
    _set_if_missing(accounts_settings, "revenue_account_id", account_ids.get("revenue"))
    _set_if_missing(accounts_settings, "expense_account_id", account_ids.get("expense"))

    # mirror top-level keys for backwards compatibility with earlier settings lookups
    for key, value in list(accounts_settings.items()):
        _set_if_missing(settings, key, UUID(value))

    if changes or needs_sync:
        settings["chart_of_accounts_mapping"] = accounts_settings
        settings["accounts"] = accounts_settings
        tenant.settings_json = settings
        return True
    return False


async def seed_tenant(session: AsyncSession, tenant: Tenant | None) -> None:
    tenant_id = tenant.id if tenant else None
    roles = await _ensure_roles(session, tenant_id)
    accounts = await _ensure_chart_of_accounts(session, tenant_id)
    mapping_changed = bool(tenant and _apply_account_mapping(tenant, accounts))
    if roles or accounts or mapping_changed:
        await session.commit()
        for entity in roles + accounts:
            await session.refresh(entity)
        if mapping_changed and tenant:
            await session.refresh(tenant)

    if roles:
        logger.info("Ensured %s roles for tenant %s", len(roles), tenant_id or "GLOBAL")
    if accounts:
        logger.info("Ensured %s chart accounts for tenant %s", len(accounts), tenant_id or "GLOBAL")
    if mapping_changed and tenant:
        logger.info("Updated account mappings for tenant %s", tenant.slug)


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
