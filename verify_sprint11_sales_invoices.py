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
        print("verify_sprint11_sales_invoices: env file not loaded; relying on process environment")
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


BACKEND_ROOT = Path(__file__).resolve().parent / "backend"
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
from app.models.account_mapping import AccountMapping
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine
from app.models.role import Role
from app.models.tenant import Tenant
from app.services import user_service


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


def _auth_headers(token: str, tenant_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-Id": str(tenant_id)}


def _quantize(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


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


async def _fetch_invoice_entries(
    session: AsyncSession, tenant_id: uuid.UUID, invoice_id: uuid.UUID
) -> list[JournalEntry]:
    result = await session.execute(
        select(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.source_type == "sales_invoice",
            JournalEntry.source_id == invoice_id,
        )
        .order_by(JournalEntry.created_at.desc())
    )
    return list(result.scalars().all())


async def _fetch_reversal_entries(
    session: AsyncSession, tenant_id: uuid.UUID, entry_id: uuid.UUID
) -> list[JournalEntry]:
    result = await session.execute(
        select(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            (JournalEntry.reversed_of_id == entry_id)
            | (JournalEntry.reversal_of_entry_id == entry_id),
        )
        .order_by(JournalEntry.created_at.desc())
    )
    return list(result.scalars().all())


async def _expect_status(
    client: AsyncClient,
    method: str,
    path: str,
    expected_status: int,
    *,
    headers: dict[str, str],
    json: dict | None = None,
    params: dict | None = None,
) -> dict:
    response = await client.request(method, path, headers=headers, json=json, params=params)
    if response.status_code != expected_status:
        raise VerificationError(
            f"{method} {path} returned {response.status_code}: {response.text}"
        )
    return response.json() if response.text else {}


async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        tenant = Tenant(
            name="Sprint 11 Sales Invoices",
            slug=f"sprint11-sales-{uuid.uuid4().hex[:8]}",
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
                "full_name": "Sprint 11 Admin",
                "role_id": admin_role.id,
            },
        )
        admin_token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )

        ar_account_id = await _get_ar_control_account_id(session, tenant_id)
        revenue_account = await session.scalar(
            select(Account)
            .where(Account.tenant_id == tenant_id, Account.type.in_(["INCOME", "REVENUE"]))
            .order_by(Account.code.asc())
        )
        if not revenue_account:
            revenue_account = await _get_or_create_account(
                session,
                tenant_id,
                code="4000",
                name="Revenue",
                account_type="INCOME",
                normal_balance="credit",
            )
        revenue_account_id = revenue_account.id

    admin_headers = _auth_headers(admin_token, tenant_id)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        customer = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=admin_headers,
            json={"code": "CUST-SI-1", "name": "Sprint 11 Invoice Customer"},
        )
        customer_id = customer.get("id")
        if not customer_id:
            raise VerificationError("customer id missing for sales invoice test")

        invoice_no = f"SI-{uuid.uuid4().hex[:8]}"
        invoice_date = date.today()
        line_one = {
            "line_no": 1,
            "description": "Consulting",
            "quantity": "1",
            "unit_price": "120.00",
            "amount": "120.00",
            "revenue_account_id": str(revenue_account_id),
        }
        line_two = {
            "line_no": 2,
            "description": "Support",
            "quantity": "1",
            "unit_price": "80.00",
            "amount": "80.00",
            "revenue_account_id": str(revenue_account_id),
        }
        total_amount = _quantize("200.00")

        draft = await _expect_status(
            client,
            "POST",
            "/api/v1/sales-invoices/",
            201,
            headers=admin_headers,
            json={
                "customer_id": customer_id,
                "invoice_no": invoice_no,
                "invoice_date": invoice_date.isoformat(),
                "currency_code": "USD",
                "lines": [line_one, line_two],
            },
        )
        invoice_id = draft.get("id")
        if not invoice_id:
            raise VerificationError("sales invoice id missing")
        if draft.get("status") != "DRAFT":
            raise VerificationError("sales invoice draft status incorrect")

    async with session_maker() as session:
        entries = await _fetch_invoice_entries(session, tenant_id, uuid.UUID(invoice_id))
        if entries:
            raise VerificationError("draft sales invoice should not create journal entry")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        posted = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/post",
            200,
            headers=admin_headers,
        )
        if posted.get("status") != "POSTED":
            raise VerificationError("sales invoice did not post")
        if not posted.get("posted_at"):
            raise VerificationError("posted_at missing after posting sales invoice")

    async with session_maker() as session:
        entries = await _fetch_invoice_entries(session, tenant_id, uuid.UUID(invoice_id))
        if len(entries) != 1:
            raise VerificationError(f"expected 1 journal entry, got {len(entries)}")
        entry = entries[0]

        lines_result = await session.execute(select(JournalLine).where(JournalLine.entry_id == entry.id))
        lines = lines_result.scalars().all()
        if not lines:
            raise VerificationError("journal entry lines missing for sales invoice")

        debit_total = sum((_quantize(line.debit_amount) for line in lines), Decimal("0.00"))
        credit_total = sum((_quantize(line.credit_amount) for line in lines), Decimal("0.00"))
        if debit_total != credit_total or debit_total != total_amount:
            raise VerificationError("sales invoice journal entry not balanced")

        debit_by_account: dict[uuid.UUID, Decimal] = {}
        credit_by_account: dict[uuid.UUID, Decimal] = {}
        for line in lines:
            if _quantize(line.debit_amount) > 0:
                debit_by_account[line.account_id] = debit_by_account.get(line.account_id, Decimal("0.00")) + _quantize(
                    line.debit_amount
                )
            if _quantize(line.credit_amount) > 0:
                credit_by_account[line.account_id] = credit_by_account.get(line.account_id, Decimal("0.00")) + _quantize(
                    line.credit_amount
                )

        ar_debit = debit_by_account.get(ar_account_id)
        if ar_debit != total_amount:
            raise VerificationError("AR control debit line incorrect")
        unexpected_debits = [account_id for account_id in debit_by_account if account_id != ar_account_id]
        if unexpected_debits:
            raise VerificationError("unexpected debit accounts in sales invoice entry")

        expected_credit_total = _quantize(line_one["amount"]) + _quantize(line_two["amount"])
        revenue_credit = credit_by_account.get(revenue_account_id, Decimal("0.00"))
        if revenue_credit != expected_credit_total:
            raise VerificationError("revenue credit total incorrect")
        unexpected_credits = [
            account_id for account_id in credit_by_account if account_id != revenue_account_id
        ]
        if unexpected_credits:
            raise VerificationError("unexpected credit accounts in sales invoice entry")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        posted_again = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/post",
            200,
            headers=admin_headers,
        )
        if posted_again.get("status") != "POSTED":
            raise VerificationError("posting again changed sales invoice status")

    async with session_maker() as session:
        entries = await _fetch_invoice_entries(session, tenant_id, uuid.UUID(invoice_id))
        if len(entries) != 1:
            raise VerificationError("posting twice created extra journal entries")
        entry = entries[0]

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reversed_invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/reverse",
            200,
            headers=admin_headers,
            json={"reason": "Sprint 11 reversal"},
        )
        if reversed_invoice.get("status") != "REVERSED":
            raise VerificationError("sales invoice did not reverse")
        if not reversed_invoice.get("reversed_at"):
            raise VerificationError("reversed_at missing after reversal")

    async with session_maker() as session:
        reversal_entries = await _fetch_reversal_entries(session, tenant_id, entry.id)
        if len(reversal_entries) != 1:
            raise VerificationError("expected one reversal journal entry")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reversed_again = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/reverse",
            200,
            headers=admin_headers,
            json={"reason": "Sprint 11 reversal again"},
        )
        if reversed_again.get("status") != "REVERSED":
            raise VerificationError("second reversal changed status unexpectedly")

    async with session_maker() as session:
        reversal_entries = await _fetch_reversal_entries(session, tenant_id, entry.id)
        if len(reversal_entries) != 1:
            raise VerificationError("second reversal created extra reversal entries")

    lock_date = invoice_date

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        lock_customer = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=admin_headers,
            json={"code": "CUST-SI-LOCK", "name": "Locked Period Customer"},
        )
        locked_customer_id = lock_customer.get("id")
        if not locked_customer_id:
            raise VerificationError("locked period customer id missing")

        lock_candidate = await _expect_status(
            client,
            "POST",
            "/api/v1/sales-invoices/",
            201,
            headers=admin_headers,
            json={
                "customer_id": locked_customer_id,
                "invoice_no": f"SI-LOCK-{uuid.uuid4().hex[:6]}",
                "invoice_date": lock_date.isoformat(),
                "currency_code": "USD",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Lock candidate",
                        "quantity": "1",
                        "unit_price": "50.00",
                        "amount": "50.00",
                        "revenue_account_id": str(revenue_account_id),
                    }
                ],
            },
        )
        lock_candidate_id = lock_candidate.get("id")
        if not lock_candidate_id:
            raise VerificationError("locked candidate invoice id missing")

        posted_candidate = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{lock_candidate_id}/post",
            200,
            headers=admin_headers,
        )
        if posted_candidate.get("status") != "POSTED":
            raise VerificationError("pre-lock invoice did not post")

        await _expect_status(
            client,
            "POST",
            "/api/v1/journals/period-locks",
            201,
            headers=admin_headers,
            json={"start_date": lock_date.isoformat(), "end_date": lock_date.isoformat()},
        )

        reverse_locked = await client.post(
            f"/api/v1/sales-invoices/{lock_candidate_id}/reverse",
            headers=admin_headers,
            json={"reason": "Locked reverse"},
        )
        if reverse_locked.status_code != 409:
            raise VerificationError("reversal in locked period did not fail")
        if reverse_locked.json().get("code") != "accounting_period_locked":
            raise VerificationError("locked period error code mismatch on reverse")

        locked_draft = await _expect_status(
            client,
            "POST",
            "/api/v1/sales-invoices/",
            201,
            headers=admin_headers,
            json={
                "customer_id": locked_customer_id,
                "invoice_no": f"SI-LOCK2-{uuid.uuid4().hex[:6]}",
                "invoice_date": lock_date.isoformat(),
                "currency_code": "USD",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Locked draft",
                        "quantity": "1",
                        "unit_price": "25.00",
                        "amount": "25.00",
                        "revenue_account_id": str(revenue_account_id),
                    }
                ],
            },
        )
        locked_draft_id = locked_draft.get("id")
        if not locked_draft_id:
            raise VerificationError("locked draft id missing")

        post_locked_draft = await client.post(
            f"/api/v1/sales-invoices/{locked_draft_id}/post",
            headers=admin_headers,
        )
        if post_locked_draft.status_code != 409:
            raise VerificationError("posting draft in locked period did not fail")
        if post_locked_draft.json().get("code") != "accounting_period_locked":
            raise VerificationError("locked period error code mismatch on draft post")

    print("Sprint 11 sales invoices verification: OK")


def main() -> None:
    try:
        asyncio.run(run())
    except VerificationError as exc:
        print(f"Sprint 11 sales invoices verification: FAILED - {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
