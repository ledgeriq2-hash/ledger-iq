from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path


def _candidate_env_paths() -> list[Path]:
    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = Path(__file__).resolve().parents[2]
    candidates = []
    for base in (backend_dir, repo_root):
        for name in (".env.local", ".env.development", ".env"):
            candidate = base / name
            if candidate.exists():
                candidates.append(candidate)
    return candidates


def _load_env_with_dotenv() -> bool:
    try:
        from dotenv import load_dotenv
    except Exception:
        return False
    loaded = False
    for path in _candidate_env_paths():
        if load_dotenv(dotenv_path=path, override=False):
            loaded = True
    return loaded


def _load_env_fallback() -> bool:
    loaded = False
    for path in _candidate_env_paths():
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, _, value = raw.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)
                loaded = True
    return loaded


def _prepare_environment() -> None:
    loaded = _load_env_with_dotenv()
    if not loaded and not _load_env_fallback():
        print("verify_sprint9: env file not loaded; relying on process environment")
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("CSRF_ENABLED", "false")
    os.environ.setdefault("BILLING_ENABLED", "false")
    os.environ.setdefault("JWT_SECRET_KEY", "dev-jwt-secret-key")
    os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "dev-jwt-refresh-secret-key")
    os.environ.setdefault("STRIPE_API_KEY", "sk_test_dummy")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://ledgeriq:ledgeriq_password@localhost:5432/ledgeriq",
    )


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


_prepare_environment()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.accounting.use_cases.lock_accounting_period import lock_accounting_period
from app.core.exceptions import AppException
from app.database import engine
from app.initial_data import seed_tenant
from app.models.account import Account
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.treasury_cash_transaction import CashTransactionStatus, CashTransactionType
from app.services import treasury_cash_service, user_service


class VerificationError(RuntimeError):
    pass


def _run_migrations() -> None:
    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(BACKEND_ROOT),
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise VerificationError("alembic upgrade head failed") from exc


async def _get_role(session: AsyncSession, tenant_id: uuid.UUID, name: str) -> Role:
    result = await session.execute(
        select(Role).where(Role.tenant_id == tenant_id, Role.name == name)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise VerificationError(f"role not found: {name}")
    return role


async def _get_or_create_account(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    code: str,
    name: str,
    account_type: str,
    normal_balance: str,
) -> Account:
    result = await session.execute(
        select(Account).where(Account.tenant_id == tenant_id, Account.code == code)
    )
    account = result.scalar_one_or_none()
    if account:
        return account

    account = Account(
        tenant_id=tenant_id,
        code=code,
        name=name,
        type=account_type,
        normal_balance=normal_balance,
        is_system=False,
        is_active=True,
    )
    session.add(account)
    await session.flush()
    return account


def _quantize(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        tenant = Tenant(
            name="Sprint 9 Verify",
            slug=f"sprint9-verify-{uuid.uuid4().hex[:8]}",
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        tenant_id = tenant.id

        await seed_tenant(session, tenant)

        admin_role = await _get_role(session, tenant_id, "ADMIN")

        admin_user = await user_service.create_user(
            session,
            tenant_id,
            {
                "email": f"admin-{tenant.slug}@example.com",
                "password": "Test1234",
                "full_name": "Sprint 9 Admin",
                "role_id": admin_role.id,
            },
        )

        cash_ledger_account = await _get_or_create_account(
            session,
            tenant_id,
            code="1100",
            name="Cash",
            account_type="ASSET",
            normal_balance="debit",
        )
        counterparty_account = await _get_or_create_account(
            session,
            tenant_id,
            code="4000",
            name="Revenue",
            account_type="INCOME",
            normal_balance="credit",
        )
        counterparty_account_id = counterparty_account.id

        other_tenant = Tenant(
            name="Sprint 9 Other",
            slug=f"sprint9-other-{uuid.uuid4().hex[:8]}",
        )
        session.add(other_tenant)
        await session.commit()
        await session.refresh(other_tenant)
        other_tenant_id = other_tenant.id
        await seed_tenant(session, other_tenant)

        other_cash_ledger = await _get_or_create_account(
            session,
            other_tenant_id,
            code="1100",
            name="Other Cash",
            account_type="ASSET",
            normal_balance="debit",
        )
        other_cash_account = await treasury_cash_service.create_cash_account(
            session,
            other_tenant_id,
            {
                "name": "Other Cash Account",
                "account_id": other_cash_ledger.id,
                "description": "Cross-tenant guard",
            },
            actor_id=admin_user.id,
        )
        other_cash_account_id = other_cash_account.id

        try:
            await treasury_cash_service.create_cash_transaction(
                session,
                tenant_id,
                {
                    "transaction_type": CashTransactionType.RECEIPT,
                    "amount": _quantize("50.00"),
                    "posting_date": date.today(),
                    "cash_account_id": other_cash_account_id,
                    "counterparty_account_id": counterparty_account_id,
                    "description": "Cross-tenant guard test",
                },
                actor_id=admin_user.id,
            )
        except AppException as exc:
            if exc.code != "cash_account_not_found":
                raise VerificationError(
                    f"expected cash_account_not_found, got {exc.code}"
                ) from exc
        else:
            raise VerificationError("cross-tenant cash account link should fail")

        cash_account = await treasury_cash_service.create_cash_account(
            session,
            tenant_id,
            {
                "name": "Main Cash",
                "account_id": cash_ledger_account.id,
                "description": "Sprint 9 cash account",
            },
            actor_id=admin_user.id,
        )
        cash_account_id = cash_account.id

        amount = _quantize("125.00")
        receipt_tx = await treasury_cash_service.create_cash_transaction(
            session,
            tenant_id,
            {
                "transaction_type": CashTransactionType.RECEIPT,
                "amount": amount,
                "posting_date": date.today(),
                "cash_account_id": cash_account_id,
                "counterparty_account_id": counterparty_account_id,
                "description": "Sprint 9 receipt",
            },
            actor_id=admin_user.id,
        )
        if receipt_tx.status != CashTransactionStatus.DRAFT:
            raise VerificationError("receipt transaction should start in DRAFT status")

        posted_tx = await treasury_cash_service.post_cash_transaction(
            session,
            tenant_id,
            receipt_tx.id,
            actor_id=admin_user.id,
        )
        if posted_tx.status != CashTransactionStatus.POSTED:
            raise VerificationError("receipt transaction did not post")
        if not posted_tx.journal_entry_id:
            raise VerificationError("posted transaction missing journal entry")

        entry = await session.get(JournalEntry, posted_tx.journal_entry_id)
        if not entry:
            raise VerificationError("journal entry not found for posted transaction")

        result = await session.execute(select(JournalLine).where(JournalLine.entry_id == entry.id))
        lines = result.scalars().all()
        if len(lines) != 2:
            raise VerificationError("expected exactly two journal lines for receipt")

        lines_by_account = {line.account_id: line for line in lines}
        cash_line = lines_by_account.get(cash_ledger_account.id)
        counter_line = lines_by_account.get(counterparty_account.id)
        if not cash_line or not counter_line:
            raise VerificationError("journal lines do not reference expected accounts")

        if _quantize(cash_line.debit_amount) != amount or _quantize(cash_line.credit_amount) != Decimal("0.00"):
            raise VerificationError("cash line debit/credit incorrect")
        if _quantize(counter_line.credit_amount) != amount or _quantize(counter_line.debit_amount) != Decimal("0.00"):
            raise VerificationError("counterparty line debit/credit incorrect")

        if _quantize(entry.total_debit_base) != amount or _quantize(entry.total_credit_base) != amount:
            raise VerificationError("journal entry totals do not balance")

        reversed_tx = await treasury_cash_service.reverse_cash_transaction(
            session,
            tenant_id,
            posted_tx.id,
            reason="Sprint 9 reversal",
            actor_id=admin_user.id,
        )
        if reversed_tx.status != CashTransactionStatus.REVERSED:
            raise VerificationError("reversal did not update transaction status")
        if not reversed_tx.reversal_journal_entry_id:
            raise VerificationError("reversal journal entry missing")

        reversal_entry = await session.get(JournalEntry, reversed_tx.reversal_journal_entry_id)
        if not reversal_entry:
            raise VerificationError("reversal journal entry not found")

        reversal_lines_result = await session.execute(
            select(JournalLine).where(JournalLine.entry_id == reversal_entry.id)
        )
        reversal_lines = reversal_lines_result.scalars().all()
        if len(reversal_lines) != 2:
            raise VerificationError("expected exactly two reversal journal lines")

        reversal_by_account = {line.account_id: line for line in reversal_lines}
        for account_id, original_line in lines_by_account.items():
            reversed_line = reversal_by_account.get(account_id)
            if not reversed_line:
                raise VerificationError("reversal line missing for account")
            if _quantize(reversed_line.debit_amount) != _quantize(original_line.credit_amount):
                raise VerificationError("reversal debit does not match original credit")
            if _quantize(reversed_line.credit_amount) != _quantize(original_line.debit_amount):
                raise VerificationError("reversal credit does not match original debit")

        lock_date = date.today()
        await lock_accounting_period(
            session,
            tenant_id=tenant_id,
            start_date=lock_date,
            end_date=lock_date,
            actor_id=admin_user.id,
            commit=True,
        )

        locked_tx = await treasury_cash_service.create_cash_transaction(
            session,
            tenant_id,
            {
                "transaction_type": CashTransactionType.RECEIPT,
                "amount": amount,
                "posting_date": lock_date,
                "cash_account_id": cash_account_id,
                "counterparty_account_id": counterparty_account_id,
                "description": "Locked period receipt",
            },
            actor_id=admin_user.id,
        )

        try:
            await treasury_cash_service.post_cash_transaction(
                session,
                tenant_id,
                locked_tx.id,
                actor_id=admin_user.id,
            )
        except AppException as exc:
            if exc.code != "accounting_period_locked":
                raise VerificationError(
                    f"expected accounting_period_locked, got {exc.code}"
                ) from exc
        else:
            raise VerificationError("posting in locked period should have failed")

    print("Sprint 9 verification: OK")


def main() -> None:
    try:
        asyncio.run(run())
    except VerificationError as exc:
        print(f"Sprint 9 verification: FAILED - {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
