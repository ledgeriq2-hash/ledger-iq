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
        print("verify_sprint18: env file not loaded; relying on process environment")
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


def _quantize(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


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
            name=f"Sprint 18 {label}",
            slug=f"sprint18-{label}-{uuid.uuid4().hex[:8]}",
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
                "full_name": f"Sprint 18 {label} Admin",
                "role_id": admin_role.id,
            },
        )
        token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )
        return tenant_id, token


async def _get_ap_control_account_id(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    result = await session.execute(
        select(AccountMapping).where(
            AccountMapping.tenant_id == tenant_id,
            AccountMapping.key == "AP_CONTROL",
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise VerificationError("AP_CONTROL account mapping missing")
    return mapping.account_id


async def _get_or_create_expense_accounts(session: AsyncSession, tenant_id: uuid.UUID) -> list[uuid.UUID]:
    result = await session.execute(
        select(Account)
        .where(Account.tenant_id == tenant_id, Account.type.in_(["EXPENSE", "EXPENSES"]))
        .order_by(Account.code.asc())
    )
    accounts = list(result.scalars().all())
    if len(accounts) >= 2:
        return [accounts[0].id, accounts[1].id]

    def _new_code(existing: set[str]) -> str:
        base = 5010
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
            name=f"Expense {code}",
            type="EXPENSE",
            normal_balance="debit",
            is_system=False,
            is_active=True,
        )
        session.add(account)
        await session.flush()
        accounts.append(account)
        existing_codes.add(code)

    await session.commit()
    return [accounts[0].id, accounts[1].id]


async def _fetch_invoice_entries(
    session: AsyncSession, tenant_id: uuid.UUID, invoice_id: uuid.UUID
) -> list[JournalEntry]:
    result = await session.execute(
        select(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.source_type == "purchase_invoice",
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
            (JournalEntry.reversed_of_id == entry_id) | (JournalEntry.reversal_of_entry_id == entry_id),
        )
        .order_by(JournalEntry.created_at.desc())
    )
    return list(result.scalars().all())


async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    tenant_a_id, token_a = await _create_tenant_with_admin(session_maker, "tenant-a")
    tenant_b_id, token_b = await _create_tenant_with_admin(session_maker, "tenant-b")

    async with session_maker() as session:
        ap_account_id = await _get_ap_control_account_id(session, tenant_a_id)
        expense_account_ids = await _get_or_create_expense_accounts(session, tenant_a_id)

    headers_a = _auth_headers(token_a, tenant_a_id)
    headers_b = _auth_headers(token_b, tenant_b_id)
    today = date.today().isoformat()

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("TEST 1: create vendor")
        vendor = await _expect_status(
            client,
            "POST",
            "/api/v1/vendors/",
            201,
            headers=headers_a,
            json={"code": "VEND-PB-1", "name": "Sprint 18 Vendor"},
        )
        vendor_id = vendor.get("id")
        if not vendor_id:
            raise VerificationError("vendor id missing")

        print("TEST 2: create draft purchase bill (no ledger impact)")
        line_one = {
            "line_no": 1,
            "description": "Office supplies",
            "quantity": "2",
            "unit_price": "50.00",
            "amount": "100.00",
            "expense_account_id": str(expense_account_ids[0]),
        }
        line_two = {
            "line_no": 2,
            "description": "Consulting",
            "quantity": "1",
            "unit_price": "75.00",
            "amount": "75.00",
            "expense_account_id": str(expense_account_ids[1]),
        }
        total_amount = _quantize("175.00")

        draft = await _expect_status(
            client,
            "POST",
            f"/api/v1/vendors/{vendor_id}/purchase-bills",
            201,
            headers=headers_a,
            json={
                "bill_no": None,
                "invoice_date": today,
                "currency_code": "USD",
                "lines": [line_one, line_two],
            },
        )
        bill_id = draft.get("id")
        if not bill_id:
            raise VerificationError("purchase bill id missing")
        if draft.get("status") != "DRAFT":
            raise VerificationError("purchase bill draft status incorrect")

    async with session_maker() as session:
        entries = await _fetch_invoice_entries(session, tenant_a_id, uuid.UUID(bill_id))
        if entries:
            raise VerificationError("draft purchase bill should not create journal entry")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("TEST 3: post purchase bill")
        posted = await _expect_status(
            client,
            "POST",
            f"/api/v1/purchase-bills/{bill_id}/post",
            200,
            headers=headers_a,
        )
        if posted.get("status") != "POSTED":
            raise VerificationError("purchase bill did not post")
        if not posted.get("posted_at"):
            raise VerificationError("posted_at missing after posting purchase bill")
        posting_entry_id = posted.get("posting_journal_entry_id")
        if not posting_entry_id:
            raise VerificationError("posting_journal_entry_id missing after posting")

    async with session_maker() as session:
        entries = await _fetch_invoice_entries(session, tenant_a_id, uuid.UUID(bill_id))
        if len(entries) != 1:
            raise VerificationError(f"expected 1 journal entry, got {len(entries)}")
        entry = entries[0]

        lines_result = await session.execute(select(JournalLine).where(JournalLine.entry_id == entry.id))
        lines = lines_result.scalars().all()
        if not lines:
            raise VerificationError("journal entry lines missing for purchase bill")

        debit_total = sum((_quantize(line.debit_base) for line in lines), Decimal("0.00"))
        credit_total = sum((_quantize(line.credit_base) for line in lines), Decimal("0.00"))
        if debit_total != credit_total or debit_total != total_amount:
            raise VerificationError("journal entry not balanced for purchase bill")

        ap_credit = sum(
            (_quantize(line.credit_base) for line in lines if line.account_id == ap_account_id),
            Decimal("0.00"),
        )
        if ap_credit != total_amount:
            raise VerificationError("AP control credit mismatch")

        expense_totals = {
            str(expense_account_ids[0]): Decimal("0.00"),
            str(expense_account_ids[1]): Decimal("0.00"),
        }
        for line in lines:
            key = str(line.account_id)
            if key in expense_totals:
                expense_totals[key] += _quantize(line.debit_base)

        if expense_totals[str(expense_account_ids[0])] != Decimal("100.00"):
            raise VerificationError("expense account 1 debit mismatch")
        if expense_totals[str(expense_account_ids[1])] != Decimal("75.00"):
            raise VerificationError("expense account 2 debit mismatch")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("TEST 4: idempotent post")
        await _expect_error(
            client,
            "POST",
            f"/api/v1/purchase-bills/{bill_id}/post",
            409,
            "purchase_invoice_already_posted",
            headers=headers_a,
        )

        print("TEST 5: period lock enforcement on reversal")
        lock = await _expect_status(
            client,
            "POST",
            "/api/v1/journals/period-locks",
            201,
            headers=headers_a,
            json={"start_date": today, "end_date": today},
        )
        lock_id = lock.get("id")

        await _expect_error(
            client,
            "POST",
            f"/api/v1/purchase-bills/{bill_id}/reverse",
            409,
            "accounting_period_locked",
            headers=headers_a,
            json={"reason": "Locked period"},
        )

        if lock_id:
            await _expect_status(
                client,
                "DELETE",
                f"/api/v1/journals/period-locks/{lock_id}",
                200,
                headers=headers_a,
            )

        print("TEST 6: reverse purchase bill")
        reversed_bill = await _expect_status(
            client,
            "POST",
            f"/api/v1/purchase-bills/{bill_id}/reverse",
            200,
            headers=headers_a,
            json={"reason": "Sprint 18 reversal"},
        )
        if reversed_bill.get("status") != "REVERSED":
            raise VerificationError("purchase bill did not reverse")
        reversal_entry_id = reversed_bill.get("reversal_journal_entry_id")
        if not reversal_entry_id:
            raise VerificationError("reversal_journal_entry_id missing after reversal")

    async with session_maker() as session:
        reversal_entries = await _fetch_reversal_entries(
            session, tenant_a_id, uuid.UUID(posting_entry_id)
        )
        if len(reversal_entries) != 1:
            raise VerificationError(f"expected 1 reversal entry, got {len(reversal_entries)}")
        reversal_entry = reversal_entries[0]
        lines_result = await session.execute(select(JournalLine).where(JournalLine.entry_id == reversal_entry.id))
        lines = lines_result.scalars().all()
        if not lines:
            raise VerificationError("reversal journal entry lines missing")
        rev_debit = sum((_quantize(line.debit_base) for line in lines), Decimal("0.00"))
        rev_credit = sum((_quantize(line.credit_base) for line in lines), Decimal("0.00"))
        if rev_debit != rev_credit:
            raise VerificationError("reversal journal entry not balanced")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("TEST 7: idempotent reverse")
        await _expect_error(
            client,
            "POST",
            f"/api/v1/purchase-bills/{bill_id}/reverse",
            409,
            "purchase_invoice_already_reversed",
            headers=headers_a,
            json={"reason": "Second reversal"},
        )

        print("TEST 8: period lock enforcement on post")
        lock = await _expect_status(
            client,
            "POST",
            "/api/v1/journals/period-locks",
            201,
            headers=headers_a,
            json={"start_date": today, "end_date": today},
        )
        lock_id = lock.get("id")

        locked_bill = await _expect_status(
            client,
            "POST",
            f"/api/v1/vendors/{vendor_id}/purchase-bills",
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
                        "expense_account_id": str(expense_account_ids[0]),
                    }
                ],
            },
        )
        locked_bill_id = locked_bill.get("id")
        if not locked_bill_id:
            raise VerificationError("locked bill id missing")

        await _expect_error(
            client,
            "POST",
            f"/api/v1/purchase-bills/{locked_bill_id}/post",
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

        print("TEST 9: tenant isolation")
        await _expect_error(
            client,
            "GET",
            f"/api/v1/purchase-bills/{bill_id}",
            404,
            "http_error",
            headers=headers_b,
        )

    print("SPRINT 18 VERIFIED OK")


if __name__ == "__main__":
    asyncio.run(run())
