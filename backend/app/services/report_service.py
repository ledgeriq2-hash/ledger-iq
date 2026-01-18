from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.redis import get_redis
from app.core.settings_utils import TenantSettingsError
from app.models.account import Account
from app.models.chart_of_account import AccountType, ChartOfAccount
from app.models.journal_entry import JournalEntry
from app.models.journal_entry_line import JournalEntryLine
from app.models.journal_line import JournalLine
from app.models.reports_cache import ReportsCache
from app.services.accounting_mapping import get_account_mapping


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _parse_data(data: str) -> Any:
    try:
        return json.loads(data)
    except Exception:
        return data


async def list_report_cache(session: AsyncSession, tenant_id: UUID) -> Sequence[ReportsCache]:
    result = await session.execute(select(ReportsCache).where(ReportsCache.tenant_id == tenant_id))
    return result.scalars().all()


async def get_report_cache(
    session: AsyncSession, tenant_id: UUID, report_type: str, params_hash: str
) -> ReportsCache | None:
    result = await session.execute(
        select(ReportsCache)
        .where(
            ReportsCache.report_type == report_type,
            ReportsCache.params_hash == params_hash,
            ReportsCache.tenant_id == tenant_id,
        )
        .order_by(ReportsCache.created_at.desc(), ReportsCache.id.desc())
        .limit(1)
    )
    return result.scalars().first()


async def save_report_cache(session: AsyncSession, tenant_id: UUID, payload: Any) -> ReportsCache:
    data = _to_dict(payload)
    cache = ReportsCache(**data, tenant_id=tenant_id)
    session.add(cache)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await get_report_cache(session, tenant_id, cache.report_type, cache.params_hash)
        return existing or cache
    await session.refresh(cache)
    return cache


async def update_report_cache(
    session: AsyncSession,
    tenant_id: UUID,
    cache_id: UUID,
    payload: Any,
) -> ReportsCache | None:
    result = await session.execute(
        select(ReportsCache).where(ReportsCache.id == cache_id, ReportsCache.tenant_id == tenant_id)
    )
    cache = result.scalar_one_or_none()
    if not cache:
        return None
    data = _to_dict(payload, exclude_unset=True)
    for field, value in data.items():
        if field in {"id", "tenant_id"}:
            continue
        setattr(cache, field, value)
    await session.commit()
    await session.refresh(cache)
    return cache


async def delete_report_cache(session: AsyncSession, tenant_id: UUID, cache_id: UUID) -> bool:
    result = await session.execute(
        delete(ReportsCache).where(ReportsCache.id == cache_id, ReportsCache.tenant_id == tenant_id)
    )
    await session.commit()
    return result.rowcount > 0


async def get_report_data(
    session: AsyncSession,
    tenant_id: UUID,
    report_type: str,
    params_hash: str,
    generator: Callable[[], Coroutine[Any, Any, Any] | Any] | None = None,
    *,
    redis_ttl: int = 180,
) -> dict[str, Any]:
    if report_type == "trial_balance" and generator:
        result = await generator() if asyncio.iscoroutinefunction(generator) else generator()
        data = await result if asyncio.iscoroutine(result) else result
        return {"report_type": report_type, "data": data, "cached": False}

    cache_key = f"report:{tenant_id}:{report_type}:{params_hash}"
    redis_client = None
    try:
        redis_client = await get_redis()
        cached_blob = await redis_client.get(cache_key)
        if cached_blob:
            return {"report_type": report_type, "data": json.loads(cached_blob), "cached": True, "source": "redis"}
    except Exception:
        redis_client = None

    cache = await get_report_cache(session, tenant_id, report_type, params_hash)
    now = datetime.now(UTC)
    if cache and (cache.expires_at is None or cache.expires_at > now):
        return {"report_type": report_type, "data": _parse_data(cache.data_json), "cached": True}

    data = None
    if generator:
        result = await generator() if asyncio.iscoroutinefunction(generator) else generator()
        data = await result if asyncio.iscoroutine(result) else result
        serialized = json.dumps(data, default=str, ensure_ascii=False)
        payload = {
            "report_type": report_type,
            "params_hash": params_hash,
            "data_json": serialized,
            "expires_at": getattr(cache, "expires_at", None),
        }
        if cache:
            await update_report_cache(session, tenant_id, cache.id, payload)
        else:
            await save_report_cache(session, tenant_id, payload)
        if redis_client:
            try:
                await redis_client.set(cache_key, serialized, ex=redis_ttl)
            except Exception:
                pass
    return {"report_type": report_type, "data": data, "cached": False}


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def _posted_entry_clause():
    return or_(
        JournalEntry.is_posted.is_(True),
        func.lower(JournalEntry.status) == "posted",
    )


def _normalize_currency(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().upper()
    return normalized or None


async def _ensure_single_currency(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    from_date: date | None,
    to_date: date | None,
    account_id: UUID | None = None,
) -> str | None:
    if to_date is None:
        return None

    base_stmt = (
        select(func.distinct(JournalEntry.base_currency))
        .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalLine.tenant_id == tenant_id,
            _posted_entry_clause(),
            JournalEntry.is_voided.is_(False),
            JournalEntry.entry_date <= to_date,
        )
    )
    if from_date is not None:
        base_stmt = base_stmt.where(JournalEntry.entry_date >= from_date)
    if account_id is not None:
        base_stmt = base_stmt.where(JournalLine.account_id == account_id)
    base_result = await session.execute(base_stmt)
    base_currencies = {
        _normalize_currency(row[0])
        for row in base_result.fetchall()
        if _normalize_currency(row[0]) is not None
    }

    if len(base_currencies) > 1:
        raise AppException(
            code="mixed_currency_report",
            message="Report data contains multiple base currencies; single-currency reports only.",
            http_status=422,
        )

    line_stmt = (
        select(func.distinct(JournalLine.line_currency))
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalLine.tenant_id == tenant_id,
            _posted_entry_clause(),
            JournalEntry.is_voided.is_(False),
            JournalEntry.entry_date <= to_date,
        )
    )
    if from_date is not None:
        line_stmt = line_stmt.where(JournalEntry.entry_date >= from_date)
    if account_id is not None:
        line_stmt = line_stmt.where(JournalLine.account_id == account_id)
    line_result = await session.execute(line_stmt)
    line_currencies = {
        _normalize_currency(row[0])
        for row in line_result.fetchall()
        if _normalize_currency(row[0]) is not None
    }

    if len(line_currencies) > 1:
        raise AppException(
            code="mixed_currency_report",
            message="Report data contains multiple line currencies; single-currency reports only.",
            http_status=422,
        )

    base_currency = next(iter(base_currencies), None)
    line_currency = next(iter(line_currencies), None)
    if base_currency and line_currency and base_currency != line_currency:
        raise AppException(
            code="mixed_currency_report",
            message="Report data contains mixed currencies; single-currency reports only.",
            http_status=422,
        )

    return base_currency or line_currency


async def _ledger_account_sums(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    before_date: date | None = None,
    account_ids: Sequence[UUID] | None = None,
) -> dict[UUID, dict[str, Decimal]]:
    stmt = (
        select(
            JournalLine.account_id,
            func.coalesce(func.sum(JournalLine.debit_base), 0).label("debit"),
            func.coalesce(func.sum(JournalLine.credit_base), 0).label("credit"),
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalLine.tenant_id == tenant_id,
            _posted_entry_clause(),
            JournalEntry.is_voided.is_(False),
        )
    )
    if from_date is not None:
        stmt = stmt.where(JournalEntry.entry_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(JournalEntry.entry_date <= to_date)
    if before_date is not None:
        stmt = stmt.where(JournalEntry.entry_date < before_date)
    if account_ids:
        stmt = stmt.where(JournalLine.account_id.in_(account_ids))

    stmt = stmt.group_by(JournalLine.account_id)
    result = await session.execute(stmt)
    totals: dict[UUID, dict[str, Decimal]] = {}
    for account_id, debit, credit in result.fetchall():
        totals[account_id] = {"debit": _decimal(debit), "credit": _decimal(credit)}
    return totals


async def _account_aggregates(
    session: AsyncSession,
    tenant_id: UUID,
    account_types: Sequence[AccountType] | None = None,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
    as_of_date: date | None = None,
    account_ids: Sequence[UUID] | None = None,
) -> list[dict[str, Any]]:
    query = (
        select(
            ChartOfAccount.id,
            ChartOfAccount.code,
            ChartOfAccount.name,
            ChartOfAccount.type,
            func.coalesce(func.sum(JournalEntryLine.debit), 0).label("debit"),
            func.coalesce(func.sum(JournalEntryLine.credit), 0).label("credit"),
        )
        .join(JournalEntryLine, JournalEntryLine.account_id == ChartOfAccount.id)
        .join(JournalEntry, JournalEntry.id == JournalEntryLine.journal_entry_id)
        .where(
            ChartOfAccount.tenant_id == tenant_id,
            JournalEntryLine.tenant_id == tenant_id,
            JournalEntry.tenant_id == tenant_id,
        )
    )
    if account_types:
        query = query.where(ChartOfAccount.type.in_(account_types))
    if account_ids:
        query = query.where(ChartOfAccount.id.in_(account_ids))
    if from_date:
        query = query.where(JournalEntry.date >= from_date)
    if to_date:
        query = query.where(JournalEntry.date <= to_date)
    if as_of_date:
        query = query.where(JournalEntry.date <= as_of_date)

    query = query.group_by(ChartOfAccount.id, ChartOfAccount.code, ChartOfAccount.name, ChartOfAccount.type)
    rows = await session.execute(query)
    aggregates: list[dict[str, Any]] = []
    for account_id, code, name, acc_type, debit, credit in rows:
        aggregates.append(
            {
                "account_id": account_id,
                "code": code,
                "name": name,
                "type": acc_type,
                "debit": _decimal(debit),
                "credit": _decimal(credit),
            }
        )
    return aggregates


async def get_income_statement(
    session: AsyncSession, tenant_id: UUID, from_date: date | None, to_date: date | None
) -> dict[str, Any]:
    revenues = await _account_aggregates(
        session,
        tenant_id,
        [AccountType.REVENUE],
        from_date=from_date,
        to_date=to_date,
    )
    expenses = await _account_aggregates(
        session,
        tenant_id,
        [AccountType.EXPENSE],
        from_date=from_date,
        to_date=to_date,
    )

    total_revenue = sum((acct["credit"] - acct["debit"]) for acct in revenues)
    total_expense = sum((acct["debit"] - acct["credit"]) for acct in expenses)
    net_income = total_revenue - total_expense

    for acct in revenues:
        acct["net"] = acct["credit"] - acct["debit"]
    for acct in expenses:
        acct["net"] = acct["debit"] - acct["credit"]

    return {
        "revenues": revenues,
        "expenses": expenses,
        "totals": {
            "revenue": total_revenue,
            "expense": total_expense,
            "net_income": net_income,
        },
        "net_income": net_income,
        "period": {"from": from_date, "to": to_date},
    }


async def get_balance_sheet(session: AsyncSession, tenant_id: UUID, as_of_date: date | None) -> dict[str, Any]:
    assets = await _account_aggregates(session, tenant_id, [AccountType.ASSET], as_of_date=as_of_date)
    liabilities = await _account_aggregates(session, tenant_id, [AccountType.LIABILITY], as_of_date=as_of_date)
    equity = await _account_aggregates(session, tenant_id, [AccountType.EQUITY], as_of_date=as_of_date)

    for acct in assets:
        acct["balance"] = acct["debit"] - acct["credit"]
    for acct in liabilities:
        acct["balance"] = acct["credit"] - acct["debit"]
    for acct in equity:
        acct["balance"] = acct["credit"] - acct["debit"]

    total_assets = sum(acct["balance"] for acct in assets)
    total_liabilities = sum(acct["balance"] for acct in liabilities)
    total_equity = sum(acct["balance"] for acct in equity)

    return {
        "as_of": as_of_date,
        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,
        "totals": {
            "assets": total_assets,
            "liabilities": total_liabilities,
            "equity": total_equity,
            "balance_check": total_assets - (total_liabilities + total_equity),
        },
    }


async def _load_cash_accounts(session: AsyncSession, tenant_id: UUID) -> list[UUID]:
    mapping = await get_account_mapping(session, tenant_id)
    cash_ids = mapping.get("cashflow_account_ids") or []
    if not cash_ids and mapping.get("cash_account_id"):
        cash_ids = [mapping["cash_account_id"]]
    if not cash_ids:
        raise TenantSettingsError("Cash/Bank account IDs are not configured for this tenant.")
    return cash_ids


async def get_cashflow_statement(
    session: AsyncSession, tenant_id: UUID, from_date: date | None, to_date: date | None
) -> dict[str, Any]:
    try:
        cash_accounts = await _load_cash_accounts(session, tenant_id)
    except TenantSettingsError:
        cash_accounts = []
    if not cash_accounts:
        return {
            "period": {"from": from_date, "to": to_date},
            "net_cash_flow": Decimal("0"),
            "accounts_used": [],
            "note": "Cashflow calculation is disabled until cash/bank accounts are configured.",
        }

    cash_movements = await _account_aggregates(
        session,
        tenant_id,
        account_types=None,
        from_date=from_date,
        to_date=to_date,
        account_ids=cash_accounts,
    )
    net_cash_flow = sum((acct["debit"] - acct["credit"]) for acct in cash_movements)

    return {
        "period": {"from": from_date, "to": to_date},
        "accounts_used": cash_accounts,
        "net_cash_flow": net_cash_flow,
        "cash_accounts": cash_movements,
        "note": "Simplified cash flow derived from configured cash/bank accounts.",
    }


async def get_trial_balance(session: AsyncSession, tenant_id: UUID, as_of_date: date | None) -> dict[str, Any]:
    aggregates = await _account_aggregates(session, tenant_id, account_types=None, as_of_date=as_of_date)
    trial_accounts: list[dict[str, Any]] = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    for acct in aggregates:
        net = acct["debit"] - acct["credit"]
        debit_balance = net if net > 0 else Decimal("0")
        credit_balance = -net if net < 0 else Decimal("0")
        total_debit += debit_balance
        total_credit += credit_balance
        trial_accounts.append(
            {
                "account_id": acct["account_id"],
                "code": acct["code"],
                "name": acct["name"],
                "type": acct["type"],
                "debit": acct["debit"],
                "credit": acct["credit"],
                "balance_debit": debit_balance,
                "balance_credit": credit_balance,
            }
        )
    return {
        "as_of": as_of_date,
        "accounts": trial_accounts,
        "totals": {"debit": total_debit, "credit": total_credit, "difference": total_debit - total_credit},
    }


async def get_trial_balance_range(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    from_date: date,
    to_date: date,
    include_zero: bool = False,
) -> dict[str, Any]:
    if from_date > to_date:
        raise AppException(
            code="invalid_date_range",
            message="from_date must be on or before to_date",
            http_status=422,
        )

    await _ensure_single_currency(session, tenant_id, from_date=None, to_date=to_date)

    opening_totals = await _ledger_account_sums(
        session,
        tenant_id,
        before_date=from_date,
    )
    period_totals = await _ledger_account_sums(
        session,
        tenant_id,
        from_date=from_date,
        to_date=to_date,
    )

    result = await session.execute(
        select(Account).where(Account.tenant_id == tenant_id).order_by(Account.code)
    )
    accounts = result.scalars().all()

    rows: list[dict[str, Any]] = []
    total_debits = Decimal("0")
    total_credits = Decimal("0")

    for account in accounts:
        opening = opening_totals.get(account.id, {"debit": Decimal("0"), "credit": Decimal("0")})
        period = period_totals.get(account.id, {"debit": Decimal("0"), "credit": Decimal("0")})

        opening_balance = opening["debit"] - opening["credit"]
        period_debits = period["debit"]
        period_credits = period["credit"]
        closing_balance = opening_balance + period_debits - period_credits

        is_zero = (
            opening_balance == 0
            and period_debits == 0
            and period_credits == 0
            and closing_balance == 0
        )
        if is_zero and not include_zero:
            continue

        rows.append(
            {
                "account_id": account.id,
                "account_code": account.code,
                "account_name": account.name,
                "account_type": account.type,
                "opening_balance": opening_balance,
                "period_debits": period_debits,
                "period_credits": period_credits,
                "closing_balance": closing_balance,
            }
        )

        total_debits += period_debits
        total_credits += period_credits

    return {
        "period": {"from": from_date, "to": to_date},
        "accounts": rows,
        "totals": {
            "period_debits": total_debits,
            "period_credits": total_credits,
            "difference": total_debits - total_credits,
        },
    }


async def get_general_ledger(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    account_id: UUID,
    from_date: date,
    to_date: date,
) -> dict[str, Any]:
    if from_date > to_date:
        raise AppException(
            code="invalid_date_range",
            message="from_date must be on or before to_date",
            http_status=422,
        )

    account = await session.get(Account, account_id)
    if not account or account.tenant_id != tenant_id:
        raise AppException(
            code="account_not_found",
            message="Account not found",
            http_status=404,
        )

    await _ensure_single_currency(
        session,
        tenant_id,
        from_date=None,
        to_date=to_date,
        account_id=account_id,
    )

    opening_totals = await _ledger_account_sums(
        session,
        tenant_id,
        before_date=from_date,
        account_ids=[account_id],
    )
    opening = opening_totals.get(account_id, {"debit": Decimal("0"), "credit": Decimal("0")})
    running_balance = opening["debit"] - opening["credit"]

    stmt = (
        select(
            JournalEntry.entry_date,
            JournalEntry.id.label("journal_id"),
            JournalLine.entry_id.label("entry_id"),
            JournalLine.id.label("line_id"),
            JournalEntry.description,
            JournalEntry.memo,
            JournalLine.memo.label("line_memo"),
            JournalLine.debit_base,
            JournalLine.credit_base,
        )
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalLine.tenant_id == tenant_id,
            JournalLine.account_id == account_id,
            _posted_entry_clause(),
            JournalEntry.is_voided.is_(False),
            JournalEntry.entry_date >= from_date,
            JournalEntry.entry_date <= to_date,
        )
        .order_by(
            JournalEntry.entry_date.asc(),
            JournalEntry.id.asc(),
            JournalLine.line_no.asc(),
            JournalLine.id.asc(),
        )
    )
    result = await session.execute(stmt)

    lines: list[dict[str, Any]] = []
    for (
        entry_date,
        journal_id,
        entry_id,
        line_id,
        description,
        memo,
        line_memo,
        debit_base,
        credit_base,
    ) in result.fetchall():
        debit = _decimal(debit_base)
        credit = _decimal(credit_base)
        running_balance += debit - credit
        lines.append(
            {
                "journal_date": entry_date,
                "journal_id": journal_id,
                "entry_id": entry_id,
                "line_id": line_id,
                "description": line_memo or memo or description,
                "debit": debit,
                "credit": credit,
                "running_balance": running_balance,
            }
        )

    return {
        "account_id": account.id,
        "account_code": account.code,
        "account_name": account.name,
        "account_type": account.type,
        "period": {"from": from_date, "to": to_date},
        "opening_balance": opening["debit"] - opening["credit"],
        "closing_balance": running_balance,
        "lines": lines,
    }
__all__ = [
    "list_report_cache",
    "get_report_cache",
    "save_report_cache",
    "update_report_cache",
    "delete_report_cache",
    "get_report_data",
    "get_income_statement",
    "get_balance_sheet",
    "get_cashflow_statement",
    "get_trial_balance",
    "get_trial_balance_range",
    "get_general_ledger",
]
