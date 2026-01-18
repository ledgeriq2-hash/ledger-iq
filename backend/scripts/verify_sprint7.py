from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import date, timedelta
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
        print("verify_sprint7: env file not loaded; relying on process environment")
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

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.database import engine
from app.initial_data import seed_tenant
from app.main import app
from app.models.account import Account
from app.models.role import Role
from app.models.tenant import Tenant
from app.schemas.journals import JournalLineCreate
from app.services import user_service
from app.services.ledger_service import LedgerService


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


def _as_decimal(value: object) -> Decimal:
    return Decimal(str(value or 0))


async def _get_role(session: AsyncSession, tenant_id: uuid.UUID, name: str) -> Role:
    result = await session.execute(
        select(Role).where(Role.tenant_id == tenant_id, Role.name == name)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise VerificationError(f"role not found: {name}")
    return role


def _pick_account(accounts: list[Account], account_type: str) -> Account:
    target = account_type.strip().upper()
    for account in accounts:
        if str(account.type).strip().upper() == target:
            return account
    raise VerificationError(f"account type not found: {account_type}")


def _auth_headers(token: str, tenant_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-Id": str(tenant_id)}


async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        tenant = Tenant(
            name="Sprint 7 Verify",
            slug=f"sprint7-verify-{uuid.uuid4().hex[:8]}",
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        tenant_id = tenant.id

        await seed_tenant(session, tenant)

        noaccess_role = Role(name="NOACCESS", permissions_json={"codes": []}, tenant_id=tenant_id)
        session.add(noaccess_role)
        await session.commit()
        await session.refresh(noaccess_role)

        admin_role = await _get_role(session, tenant_id, "ADMIN")

        admin_user = await user_service.create_user(
            session,
            tenant_id,
            {
                "email": f"admin-{tenant.slug}@example.com",
                "password": "Test1234",
                "full_name": "Sprint 7 Admin",
                "role_id": admin_role.id,
            },
        )
        noaccess_user = await user_service.create_user(
            session,
            tenant_id,
            {
                "email": f"noaccess-{tenant.slug}@example.com",
                "password": "Test1234",
                "full_name": "Sprint 7 NoAccess",
                "role_id": noaccess_role.id,
            },
        )

        admin_token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )
        noaccess_token = create_access_token(
            str(noaccess_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )

        accounts_result = await session.execute(
            select(Account).where(Account.tenant_id == tenant_id).order_by(Account.code.asc())
        )
        accounts = accounts_result.scalars().all()

        asset_account = _pick_account(accounts, "ASSET")
        liability_account = _pick_account(accounts, "LIABILITY")
        expense_account = _pick_account(accounts, "EXPENSE")
        income_account = _pick_account(accounts, "INCOME")

        service = LedgerService(session=session, tenant_id=tenant_id, actor_id=admin_user.id)
        date_one = date.today() - timedelta(days=10)
        date_two = date.today() - timedelta(days=5)
        future_date = date.today() + timedelta(days=1)

        entry_one = await service.create_manual_entry(
            entry_date=date_one,
            base_currency="USD",
            memo="Sprint 7 entry one",
            source_type="manual",
            source_id=None,
            lines=[
                JournalLineCreate(
                    account_id=asset_account.id,
                    debit_amount=Decimal("100.00"),
                    credit_amount=Decimal("0.00"),
                    line_currency="USD",
                ),
                JournalLineCreate(
                    account_id=liability_account.id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=Decimal("100.00"),
                    line_currency="USD",
                ),
            ],
        )
        await service.post_entry(entry_one.id)

        entry_two = await service.create_manual_entry(
            entry_date=date_two,
            base_currency="USD",
            memo="Sprint 7 entry two",
            source_type="manual",
            source_id=None,
            lines=[
                JournalLineCreate(
                    account_id=expense_account.id,
                    debit_amount=Decimal("50.00"),
                    credit_amount=Decimal("0.00"),
                    line_currency="USD",
                ),
                JournalLineCreate(
                    account_id=liability_account.id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=Decimal("50.00"),
                    line_currency="USD",
                ),
            ],
        )
        await service.post_entry(entry_two.id)

        reversal = await service.reverse_entry(entry_one.id, reason="Sprint 7 reversal")
        if reversal.reversal_of_entry_id != entry_one.id:
            raise VerificationError("reversal entry did not reference original entry")

        draft_entry = await service.create_manual_entry(
            entry_date=date_two,
            base_currency="USD",
            memo="Sprint 7 draft entry",
            source_type="manual",
            source_id=None,
            lines=[
                JournalLineCreate(
                    account_id=asset_account.id,
                    debit_amount=Decimal("25.00"),
                    credit_amount=Decimal("0.00"),
                    line_currency="USD",
                ),
                JournalLineCreate(
                    account_id=liability_account.id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=Decimal("25.00"),
                    line_currency="USD",
                ),
            ],
        )
        if draft_entry.status.lower() != "draft":
            raise VerificationError("draft entry was unexpectedly posted")

        mixed_entry = await service.create_manual_entry(
            entry_date=future_date,
            base_currency="EUR",
            memo="Sprint 7 mixed currency",
            source_type="manual",
            source_id=None,
            lines=[
                JournalLineCreate(
                    account_id=asset_account.id,
                    debit_amount=Decimal("10.00"),
                    credit_amount=Decimal("0.00"),
                    line_currency="EUR",
                ),
                JournalLineCreate(
                    account_id=liability_account.id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=Decimal("10.00"),
                    line_currency="EUR",
                ),
            ],
        )
        await service.post_entry(mixed_entry.id)

    admin_headers = _auth_headers(admin_token, tenant_id)
    noaccess_headers = _auth_headers(noaccess_token, tenant_id)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tb_response = await client.get(
            "/api/v1/reports/trial-balance",
            params={"from_date": date_one.isoformat(), "to_date": date.today().isoformat()},
            headers=admin_headers,
        )
        if tb_response.status_code != 200:
            raise VerificationError(f"trial balance failed: {tb_response.status_code} {tb_response.text}")

        tb_payload = tb_response.json().get("data") or {}
        tb_accounts = tb_payload.get("accounts") or []
        tb_lookup = {str(row.get("account_id")): row for row in tb_accounts}

        def _row(account: Account) -> dict:
            row = tb_lookup.get(str(account.id))
            if not row:
                raise VerificationError(f"trial balance missing account {account.code}")
            return row

        asset_row = _row(asset_account)
        liability_row = _row(liability_account)
        expense_row = _row(expense_account)

        if _as_decimal(asset_row.get("period_debits")) != Decimal("100.00"):
            raise VerificationError("trial balance asset debits incorrect")
        if _as_decimal(asset_row.get("period_credits")) != Decimal("100.00"):
            raise VerificationError("trial balance asset credits incorrect")
        if _as_decimal(asset_row.get("closing_balance")) != Decimal("0"):
            raise VerificationError("trial balance asset closing incorrect")

        if _as_decimal(liability_row.get("period_debits")) != Decimal("100.00"):
            raise VerificationError("trial balance liability debits incorrect")
        if _as_decimal(liability_row.get("period_credits")) != Decimal("150.00"):
            raise VerificationError("trial balance liability credits incorrect")
        if _as_decimal(liability_row.get("closing_balance")) != Decimal("-50.00"):
            raise VerificationError("trial balance liability closing incorrect")

        if _as_decimal(expense_row.get("period_debits")) != Decimal("50.00"):
            raise VerificationError("trial balance expense debits incorrect")
        if _as_decimal(expense_row.get("period_credits")) != Decimal("0"):
            raise VerificationError("trial balance expense credits incorrect")
        if _as_decimal(expense_row.get("closing_balance")) != Decimal("50.00"):
            raise VerificationError("trial balance expense closing incorrect")

        totals = tb_payload.get("totals") or {}
        if _as_decimal(totals.get("difference")) != Decimal("0"):
            raise VerificationError("trial balance totals not balanced")

        tb_zero_response = await client.get(
            "/api/v1/reports/trial-balance",
            params={
                "from_date": date_one.isoformat(),
                "to_date": date.today().isoformat(),
                "include_zero": "true",
            },
            headers=admin_headers,
        )
        if tb_zero_response.status_code != 200:
            raise VerificationError(f"include_zero trial balance failed: {tb_zero_response.text}")
        tb_zero_accounts = tb_zero_response.json().get("data", {}).get("accounts") or []
        if str(income_account.id) not in {str(row.get("account_id")) for row in tb_zero_accounts}:
            raise VerificationError("include_zero did not include zero-balance account")

        gl_response = await client.get(
            f"/api/v1/reports/general-ledger/{liability_account.id}",
            params={"from_date": date_one.isoformat(), "to_date": date.today().isoformat()},
            headers=admin_headers,
        )
        if gl_response.status_code != 200:
            raise VerificationError(f"general ledger failed: {gl_response.status_code} {gl_response.text}")

        gl_payload = gl_response.json().get("data") or {}
        gl_lines = gl_payload.get("lines") or []
        if len(gl_lines) != 3:
            raise VerificationError(f"general ledger lines unexpected count: {len(gl_lines)}")

        running_values = [_as_decimal(line.get("running_balance")) for line in gl_lines]
        if running_values != [Decimal("-100.00"), Decimal("-150.00"), Decimal("-50.00")]:
            raise VerificationError("general ledger running balance incorrect")

        mixed_response = await client.get(
            "/api/v1/reports/trial-balance",
            params={"from_date": date_one.isoformat(), "to_date": future_date.isoformat()},
            headers=admin_headers,
        )
        if mixed_response.status_code != 422:
            raise VerificationError("mixed currency data did not raise error")
        if mixed_response.json().get("code") != "mixed_currency_report":
            raise VerificationError("mixed currency error code missing")

        deny_response = await client.get(
            "/api/v1/reports/trial-balance",
            params={"from_date": date_one.isoformat(), "to_date": date.today().isoformat()},
            headers=noaccess_headers,
        )
        if deny_response.status_code != 403:
            raise VerificationError("permission enforcement failed for reports")

    print("Sprint 7 verification: OK")


def main() -> None:
    try:
        asyncio.run(run())
    except VerificationError as exc:
        print(f"Sprint 7 verification: FAILED - {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
