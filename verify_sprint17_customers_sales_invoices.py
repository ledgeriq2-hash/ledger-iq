from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path


def _candidate_env_paths() -> list[Path]:
    repo_root = Path(__file__).resolve().parent
    backend_dir = repo_root / "backend"
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
        print("verify_sprint17: env file not loaded; relying on process environment")
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("CSRF_ENABLED", "false")
    os.environ.setdefault("BILLING_ENABLED", "false")
    os.environ.setdefault("FEATURE_OPTIONAL_ROUTES", "true")
    os.environ.setdefault("JWT_SECRET_KEY", "dev-jwt-secret-key")
    os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "dev-jwt-refresh-secret-key")
    os.environ.setdefault("STRIPE_API_KEY", "sk_test_dummy")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://ledgeriq:ledgeriq_password@localhost:5432/ledgeriq_dev",
    )


BACKEND_ROOT = Path(__file__).resolve().parent / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


_prepare_environment()

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.database import engine  # noqa: E402
from app.initial_data import seed_tenant  # noqa: E402
from app.main import app  # noqa: E402
from app.models.account import Account  # noqa: E402
from app.models.account_mapping import AccountMapping  # noqa: E402
from app.models.journal_entry import JournalEntry  # noqa: E402
from app.models.journal_line import JournalLine  # noqa: E402
from app.models.role import Role  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.services import user_service  # noqa: E402


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
    result = await session.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name == name))
    role = result.scalar_one_or_none()
    if not role:
        raise VerificationError(f"role not found: {name}")
    return role


def _auth_headers(token: str, tenant_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-Id": str(tenant_id)}


async def _expect_status(
    client: AsyncClient,
    method: str,
    path: str,
    expected_status: int,
    *,
    headers: dict[str, str],
    json: dict | None = None,
    params: dict | None = None,
) -> dict | list:
    response = await client.request(method, path, headers=headers, json=json, params=params)
    if response.status_code != expected_status:
        raise VerificationError(f"{method} {path} returned {response.status_code}: {response.text}")
    return response.json() if response.text else {}


async def _expect_error(
    client: AsyncClient,
    method: str,
    path: str,
    expected_status: int,
    expected_code: str,
    *,
    headers: dict[str, str],
    json: dict | None = None,
    params: dict | None = None,
) -> dict:
    response = await client.request(method, path, headers=headers, json=json, params=params)
    if response.status_code != expected_status:
        raise VerificationError(f"{method} {path} returned {response.status_code}: {response.text}")
    payload = response.json() if response.text else {}
    code = payload.get("code")
    if code != expected_code:
        raise VerificationError(f"{method} {path} error code mismatch: expected {expected_code}, got {code}")
    return payload


async def _create_tenant_with_admin(
    session_maker: async_sessionmaker[AsyncSession],
    label: str,
) -> tuple[uuid.UUID, str]:
    async with session_maker() as session:
        tenant = Tenant(
            name=f"Sprint 17 {label}",
            slug=f"sprint17-{label}-{uuid.uuid4().hex[:8]}",
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
                "full_name": f"Sprint 17 {label} Admin",
                "role_id": admin_role.id,
            },
        )
        token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )
        return tenant_id, token


async def _get_ar_control_account_id(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    result = await session.execute(
        select(AccountMapping).where(
            AccountMapping.tenant_id == tenant_id,
            AccountMapping.key == "AR_CONTROL",
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise VerificationError("AR_CONTROL account mapping missing")
    return mapping.account_id


async def _get_or_create_revenue_accounts(session: AsyncSession, tenant_id: uuid.UUID) -> list[uuid.UUID]:
    result = await session.execute(
        select(Account)
        .where(Account.tenant_id == tenant_id, Account.type.in_(["INCOME", "REVENUE"]))
        .order_by(Account.code.asc())
    )
    accounts = list(result.scalars().all())
    if len(accounts) >= 2:
        return [accounts[0].id, accounts[1].id]

    def _new_code(existing: set[str]) -> str:
        base = 4010
        while True:
            code = str(base)
            if code not in existing:
                return code
            base += 10

    existing_codes = {acct.code for acct in accounts}
    for _ in range(2 - len(accounts)):
        code = _new_code(existing_codes)
        account = Account(
            tenant_id=tenant_id,
            code=code,
            name=f"Revenue {code}",
            type="INCOME",
            normal_balance="credit",
            is_system=False,
            is_active=True,
        )
        session.add(account)
        await session.flush()
        accounts.append(account)
        existing_codes.add(code)

    await session.commit()
    return [accounts[0].id, accounts[1].id]


async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    tenant_a_id, token_a = await _create_tenant_with_admin(session_maker, "tenant-a")
    tenant_b_id, token_b = await _create_tenant_with_admin(session_maker, "tenant-b")

    async with session_maker() as session:
        ar_account_id = await _get_ar_control_account_id(session, tenant_a_id)
        revenue_account_ids = await _get_or_create_revenue_accounts(session, tenant_a_id)

    headers_a = _auth_headers(token_a, tenant_a_id)
    headers_b = _auth_headers(token_b, tenant_b_id)
    today = date.today().isoformat()

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("TEST 1: create customer")
        customer = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=headers_a,
            json={
                "name": "Sprint 17 Customer",
                "email": "customer@example.com",
                "phone": "+1-555-0100",
            },
        )
        customer_id = customer.get("id")
        if not customer_id:
            raise VerificationError("customer id missing")

        print("TEST 2: create draft invoice (no ledger impact)")
        draft = await _expect_status(
            client,
            "POST",
            f"/api/v1/customers/{customer_id}/sales-invoices",
            201,
            headers=headers_a,
            json={
                "invoice_date": today,
                "currency_code": "USD",
                "memo": "Sprint 17 draft",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Services A",
                        "quantity": "2",
                        "unit_price": "50.00",
                        "amount": "100.00",
                        "revenue_account_id": str(revenue_account_ids[0]),
                    },
                    {
                        "line_no": 2,
                        "description": "Services B",
                        "quantity": "1",
                        "unit_price": "75.00",
                        "amount": "75.00",
                        "revenue_account_id": str(revenue_account_ids[1]),
                    },
                ],
            },
        )
        invoice_id = draft.get("id")
        if not invoice_id:
            raise VerificationError("draft invoice id missing")
        if draft.get("status") != "DRAFT":
            raise VerificationError("draft invoice status mismatch")

        async with session_maker() as session:
            entry_count = await session.scalar(
                select(func.count())
                .select_from(JournalEntry)
                .where(
                    JournalEntry.tenant_id == tenant_a_id,
                    JournalEntry.source_type == "sales_invoice",
                    JournalEntry.source_id == uuid.UUID(invoice_id),
                )
            )
        if int(entry_count or 0) != 0:
            raise VerificationError("draft invoice created journal entries")

        print("TEST 3: post invoice")
        posted = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/post",
            200,
            headers=headers_a,
        )
        if posted.get("status") != "POSTED":
            raise VerificationError("invoice did not post")
        if not posted.get("invoice_no"):
            raise VerificationError("invoice number not assigned on post")
        posting_entry_id = posted.get("posting_journal_entry_id")
        if not posting_entry_id:
            raise VerificationError("posting_journal_entry_id missing")

        async with session_maker() as session:
            entry = await session.scalar(
                select(JournalEntry).where(
                    JournalEntry.tenant_id == tenant_a_id,
                    JournalEntry.id == uuid.UUID(posting_entry_id),
                )
            )
            if not entry:
                raise VerificationError("posting journal entry missing")
            lines = await session.execute(
                select(JournalLine).where(
                    JournalLine.tenant_id == tenant_a_id,
                    JournalLine.entry_id == uuid.UUID(posting_entry_id),
                )
            )
            lines = list(lines.scalars().all())
            debit_total = sum((line.debit_base for line in lines), Decimal("0.00"))
            credit_total = sum((line.credit_base for line in lines), Decimal("0.00"))
            if debit_total != credit_total:
                raise VerificationError("posted journal entry is not balanced")

            ar_debit = sum(
                (line.debit_base for line in lines if line.account_id == ar_account_id),
                Decimal("0.00"),
            )
            if ar_debit != Decimal("175.00"):
                raise VerificationError("AR debit amount mismatch")

            revenue_credit_totals = {
                str(revenue_account_ids[0]): Decimal("0.00"),
                str(revenue_account_ids[1]): Decimal("0.00"),
            }
            for line in lines:
                if str(line.account_id) in revenue_credit_totals:
                    revenue_credit_totals[str(line.account_id)] += line.credit_base
            if revenue_credit_totals[str(revenue_account_ids[0])] != Decimal("100.00"):
                raise VerificationError("revenue account 1 credit mismatch")
            if revenue_credit_totals[str(revenue_account_ids[1])] != Decimal("75.00"):
                raise VerificationError("revenue account 2 credit mismatch")

        print("TEST 4: idempotent post")
        await _expect_error(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/post",
            409,
            "sales_invoice_already_posted",
            headers=headers_a,
        )

        async with session_maker() as session:
            je_count = await session.scalar(
                select(func.count())
                .select_from(JournalEntry)
                .where(
                    JournalEntry.tenant_id == tenant_a_id,
                    JournalEntry.source_type == "sales_invoice",
                    JournalEntry.source_id == uuid.UUID(invoice_id),
                )
            )
        if int(je_count or 0) != 1:
            raise VerificationError("double post created extra journal entries")

        print("TEST 5: reverse invoice")
        reversed_invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/reverse",
            200,
            headers=headers_a,
            json={"reason": "Sprint 17 reversal"},
        )
        if reversed_invoice.get("status") != "REVERSED":
            raise VerificationError("invoice did not reverse")
        reversal_entry_id = reversed_invoice.get("reversal_journal_entry_id")
        if not reversal_entry_id:
            raise VerificationError("reversal_journal_entry_id missing")

        async with session_maker() as session:
            reversal_lines = await session.execute(
                select(JournalLine).where(
                    JournalLine.tenant_id == tenant_a_id,
                    JournalLine.entry_id == uuid.UUID(reversal_entry_id),
                )
            )
            reversal_lines = list(reversal_lines.scalars().all())
            rev_debit = sum((line.debit_base for line in reversal_lines), Decimal("0.00"))
            rev_credit = sum((line.credit_base for line in reversal_lines), Decimal("0.00"))
            if rev_debit != rev_credit:
                raise VerificationError("reversal journal entry not balanced")

            reversal_count = await session.scalar(
                select(func.count())
                .select_from(JournalEntry)
                .where(
                    JournalEntry.tenant_id == tenant_a_id,
                    JournalEntry.reversed_of_id == uuid.UUID(posting_entry_id),
                )
            )
        if int(reversal_count or 0) != 1:
            raise VerificationError("unexpected number of reversal journal entries")

        print("TEST 6: idempotent reverse")
        await _expect_error(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/reverse",
            409,
            "sales_invoice_already_reversed",
            headers=headers_a,
            json={"reason": "Second reversal"},
        )

        print("TEST 7: period lock enforcement")
        lock = await _expect_status(
            client,
            "POST",
            "/api/v1/journals/period-locks",
            201,
            headers=headers_a,
            json={"start_date": today, "end_date": today},
        )
        lock_id = lock.get("id")

        locked_invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/customers/{customer_id}/sales-invoices",
            201,
            headers=headers_a,
            json={
                "invoice_date": today,
                "currency_code": "USD",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Locked line",
                        "quantity": "1",
                        "unit_price": "10.00",
                        "amount": "10.00",
                        "revenue_account_id": str(revenue_account_ids[0]),
                    }
                ],
            },
        )
        locked_invoice_id = locked_invoice.get("id")
        if not locked_invoice_id:
            raise VerificationError("locked invoice id missing")

        await _expect_error(
            client,
            "POST",
            f"/api/v1/sales-invoices/{locked_invoice_id}/post",
            409,
            "accounting_period_locked",
            headers=headers_a,
        )

        if lock_id:
            await _expect_status(
                client,
                "DELETE",
                f"/api/v1/journals/period-locks/{lock_id}",
                200,
                headers=headers_a,
            )

        print("TEST 8: tenant isolation")
        await _expect_error(
            client,
            "GET",
            f"/api/v1/sales-invoices/{invoice_id}",
            404,
            "http_error",
            headers=headers_b,
        )

    print("SPRINT 17 VERIFIED OK")


if __name__ == "__main__":
    asyncio.run(run())
