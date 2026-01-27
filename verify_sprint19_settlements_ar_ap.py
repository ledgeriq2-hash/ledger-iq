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
    candidates: list[Path] = []
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
        print("verify_sprint19: env file not loaded; relying on process environment")
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
            name=f"Sprint 19 {label}",
            slug=f"sprint19-{label}-{uuid.uuid4().hex[:8]}",
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
                "full_name": f"Sprint 19 {label} Admin",
                "role_id": admin_role.id,
            },
        )
        token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )
        return tenant_id, token


async def _get_account_mapping(session: AsyncSession, tenant_id: uuid.UUID, key: str) -> AccountMapping | None:
    result = await session.execute(
        select(AccountMapping).where(
            AccountMapping.tenant_id == tenant_id,
            AccountMapping.key == key,
        )
    )
    return result.scalar_one_or_none()


async def _ensure_account_mapping(session: AsyncSession, tenant_id: uuid.UUID, key: str, account_id: uuid.UUID) -> None:
    mapping = await _get_account_mapping(session, tenant_id, key)
    if mapping:
        if mapping.account_id != account_id:
            mapping.account_id = account_id
        await session.commit()
        return
    mapping = AccountMapping(tenant_id=tenant_id, key=key, account_id=account_id)
    session.add(mapping)
    await session.commit()


async def _get_ar_control_account_id(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    mapping = await _get_account_mapping(session, tenant_id, "AR_CONTROL")
    if not mapping:
        raise VerificationError("AR_CONTROL account mapping missing")
    return mapping.account_id


async def _get_ap_control_account_id(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    mapping = await _get_account_mapping(session, tenant_id, "AP_CONTROL")
    if not mapping:
        raise VerificationError("AP_CONTROL account mapping missing")
    return mapping.account_id


async def _get_cash_account_id(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    result = await session.execute(
        select(Account)
        .where(
            Account.tenant_id == tenant_id,
            Account.type == "ASSET",
            Account.is_active.is_(True),
        )
        .order_by(Account.code.asc())
    )
    accounts = list(result.scalars().all())
    for account in accounts:
        if account.code in {"1100", "1200"} or account.name.lower() in {"cash", "bank"}:
            return account.id
    if accounts:
        return accounts[0].id
    raise VerificationError("cash/bank account not found")


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


async def _get_or_create_account(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str,
    base_code: int,
    account_type: str,
    normal_balance: str,
) -> uuid.UUID:
    result = await session.execute(
        select(Account).where(Account.tenant_id == tenant_id, func.lower(Account.name) == name.lower())
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing.id

    existing_codes = {
        code for (code,) in (await session.execute(select(Account.code).where(Account.tenant_id == tenant_id))).all()
    }
    code = base_code
    while str(code) in existing_codes:
        code += 10

    account = Account(
        tenant_id=tenant_id,
        code=str(code),
        name=name,
        type=account_type,
        normal_balance=normal_balance,
        is_system=False,
        is_active=True,
    )
    session.add(account)
    await session.commit()
    return account.id


async def _fetch_entries(
    session: AsyncSession, tenant_id: uuid.UUID, source_type: str, source_id: uuid.UUID
) -> list[JournalEntry]:
    result = await session.execute(
        select(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.source_type == source_type,
            JournalEntry.source_id == source_id,
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


async def _fetch_entry_lines(
    session: AsyncSession, tenant_id: uuid.UUID, entry_id: uuid.UUID
) -> list[JournalLine]:
    result = await session.execute(
        select(JournalLine).where(
            JournalLine.tenant_id == tenant_id,
            JournalLine.entry_id == entry_id,
        )
    )
    return list(result.scalars().all())


async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    tenant_a_id, token_a = await _create_tenant_with_admin(session_maker, "tenant-a")
    tenant_b_id, token_b = await _create_tenant_with_admin(session_maker, "tenant-b")

    async with session_maker() as session:
        ar_account_id = await _get_ar_control_account_id(session, tenant_a_id)
        ap_account_id = await _get_ap_control_account_id(session, tenant_a_id)
        revenue_account_ids = await _get_or_create_revenue_accounts(session, tenant_a_id)
        expense_account_ids = await _get_or_create_expense_accounts(session, tenant_a_id)
        cash_account_id = await _get_cash_account_id(session, tenant_a_id)
        customer_credit_account_id = await _get_or_create_account(
            session,
            tenant_a_id,
            name="Customer Credits",
            base_code=2300,
            account_type="LIABILITY",
            normal_balance="credit",
        )
        vendor_prepay_account_id = await _get_or_create_account(
            session,
            tenant_a_id,
            name="Vendor Prepayments",
            base_code=1350,
            account_type="ASSET",
            normal_balance="debit",
        )
        await _ensure_account_mapping(session, tenant_a_id, "CUSTOMER_CREDIT", customer_credit_account_id)
        await _ensure_account_mapping(session, tenant_a_id, "VENDOR_PREPAY", vendor_prepay_account_id)

    headers_a = _auth_headers(token_a, tenant_a_id)
    headers_b = _auth_headers(token_b, tenant_b_id)
    today = date.today().isoformat()

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("TEST 1: create customer and vendor")
        customer = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=headers_a,
            json={"code": "CUST-AR-1", "name": "Sprint 19 Customer"},
        )
        customer_id = customer.get("id")
        if not customer_id:
            raise VerificationError("customer id missing")

        vendor = await _expect_status(
            client,
            "POST",
            "/api/v1/vendors/",
            201,
            headers=headers_a,
            json={"code": "VEND-AP-1", "name": "Sprint 19 Vendor"},
        )
        vendor_id = vendor.get("id")
        if not vendor_id:
            raise VerificationError("vendor id missing")

        print("TEST 2: create and post sales invoice")
        invoice_lines = [
            {
                "line_no": 1,
                "description": "Service A",
                "quantity": "1",
                "unit_price": "60.00",
                "amount": "60.00",
                "revenue_account_id": str(revenue_account_ids[0]),
            },
            {
                "line_no": 2,
                "description": "Service B",
                "quantity": "1",
                "unit_price": "40.00",
                "amount": "40.00",
                "revenue_account_id": str(revenue_account_ids[1]),
            },
        ]
        invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/customers/{customer_id}/sales-invoices",
            201,
            headers=headers_a,
            json={"invoice_date": today, "currency_code": "USD", "lines": invoice_lines},
        )
        invoice_id = invoice.get("id")
        if not invoice_id:
            raise VerificationError("sales invoice id missing")
        posted_invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/post",
            200,
            headers=headers_a,
        )
        if posted_invoice.get("status") != "POSTED":
            raise VerificationError("sales invoice did not post")

        print("TEST 3: create and post purchase bill")
        bill_lines = [
            {
                "line_no": 1,
                "description": "Supplies",
                "quantity": "1",
                "unit_price": "120.00",
                "amount": "120.00",
                "expense_account_id": str(expense_account_ids[0]),
            },
            {
                "line_no": 2,
                "description": "Consulting",
                "quantity": "1",
                "unit_price": "80.00",
                "amount": "80.00",
                "expense_account_id": str(expense_account_ids[1]),
            },
        ]
        bill = await _expect_status(
            client,
            "POST",
            f"/api/v1/vendors/{vendor_id}/purchase-bills",
            201,
            headers=headers_a,
            json={"invoice_date": today, "currency_code": "USD", "lines": bill_lines},
        )
        bill_id = bill.get("id")
        if not bill_id:
            raise VerificationError("purchase bill id missing")
        posted_bill = await _expect_status(
            client,
            "POST",
            f"/api/v1/purchase-bills/{bill_id}/post",
            200,
            headers=headers_a,
        )
        if posted_bill.get("status") != "POSTED":
            raise VerificationError("purchase bill did not post")

        print("TEST 4: create draft customer receipt (no ledger impact)")
        receipt = await _expect_status(
            client,
            "POST",
            f"/api/v1/customers/{customer_id}/receipts",
            201,
            headers=headers_a,
            json={
                "receipt_date": today,
                "amount_total": "120.00",
                "cash_account_id": str(cash_account_id),
                "currency_code": "USD",
            },
        )
        receipt_id = receipt.get("id")
        if not receipt_id:
            raise VerificationError("receipt id missing")

    async with session_maker() as session:
        receipt_entries = await _fetch_entries(session, tenant_a_id, "customer_receipt", uuid.UUID(receipt_id))
        if receipt_entries:
            raise VerificationError("draft receipt should not create journal entry")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _expect_status(
            client,
            "POST",
            f"/api/v1/receipts/{receipt_id}/allocations",
            201,
            headers=headers_a,
            json={"sales_invoice_id": invoice_id, "amount": "100.00"},
        )

        print("TEST 5: post customer receipt")
        posted_receipt = await _expect_status(
            client,
            "POST",
            f"/api/v1/receipts/{receipt_id}/post",
            200,
            headers=headers_a,
        )
        if posted_receipt.get("status") != "POSTED":
            raise VerificationError("receipt did not post")
        if not posted_receipt.get("receipt_no"):
            raise VerificationError("receipt_no not assigned on posting")
        receipt_entry_id = posted_receipt.get("posting_journal_entry_id")
        if not receipt_entry_id:
            raise VerificationError("receipt posting journal entry missing")

    async with session_maker() as session:
        receipt_entries = await _fetch_entries(session, tenant_a_id, "customer_receipt", uuid.UUID(receipt_id))
        if len(receipt_entries) != 1:
            raise VerificationError("receipt should have exactly one journal entry after posting")
        entry_lines = await _fetch_entry_lines(session, tenant_a_id, uuid.UUID(receipt_entry_id))
        if not entry_lines:
            raise VerificationError("receipt journal entry lines missing")
        debit_total = sum((line.debit_base for line in entry_lines), Decimal("0.00"))
        credit_total = sum((line.credit_base for line in entry_lines), Decimal("0.00"))
        if _quantize(debit_total) != _quantize(credit_total):
            raise VerificationError("receipt journal entry not balanced")
        totals_by_account = {str(cash_account_id): Decimal("0.00"), str(ar_account_id): Decimal("0.00"), str(customer_credit_account_id): Decimal("0.00")}
        for line in entry_lines:
            account_id = str(line.account_id)
            if account_id in totals_by_account:
                totals_by_account[account_id] += _quantize(line.debit_base) - _quantize(line.credit_base)
        if totals_by_account[str(cash_account_id)] != Decimal("120.00"):
            raise VerificationError("cash debit for receipt incorrect")
        if totals_by_account[str(ar_account_id)] != Decimal("-100.00"):
            raise VerificationError("AR credit for receipt incorrect")
        if totals_by_account[str(customer_credit_account_id)] != Decimal("-20.00"):
            raise VerificationError("customer credit liability incorrect")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _expect_error(
            client,
            "POST",
            f"/api/v1/receipts/{receipt_id}/post",
            409,
            "customer_receipt_already_posted",
            headers=headers_a,
        )
        async with session_maker() as session:
            receipt_entries = await _fetch_entries(session, tenant_a_id, "customer_receipt", uuid.UUID(receipt_id))
            if len(receipt_entries) != 1:
                raise VerificationError("double-post created extra receipt journal entries")

        print("TEST 6: create draft vendor payment (no ledger impact)")
        payment = await _expect_status(
            client,
            "POST",
            f"/api/v1/vendors/{vendor_id}/payments",
            201,
            headers=headers_a,
            json={
                "payment_date": today,
                "amount_total": "250.00",
                "cash_account_id": str(cash_account_id),
                "currency_code": "USD",
            },
        )
        payment_id = payment.get("id")
        if not payment_id:
            raise VerificationError("payment id missing")

    async with session_maker() as session:
        payment_entries = await _fetch_entries(session, tenant_a_id, "vendor_payment", uuid.UUID(payment_id))
        if payment_entries:
            raise VerificationError("draft payment should not create journal entry")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _expect_status(
            client,
            "POST",
            f"/api/v1/payments/{payment_id}/allocations",
            201,
            headers=headers_a,
            json={"purchase_bill_id": bill_id, "amount": "200.00"},
        )

        print("TEST 7: post vendor payment")
        posted_payment = await _expect_status(
            client,
            "POST",
            f"/api/v1/payments/{payment_id}/post",
            200,
            headers=headers_a,
        )
        if posted_payment.get("status") != "POSTED":
            raise VerificationError("payment did not post")
        if not posted_payment.get("payment_no"):
            raise VerificationError("payment_no not assigned on posting")
        payment_entry_id = posted_payment.get("posting_journal_entry_id")
        if not payment_entry_id:
            raise VerificationError("payment posting journal entry missing")

    async with session_maker() as session:
        entry_lines = await _fetch_entry_lines(session, tenant_a_id, uuid.UUID(payment_entry_id))
        if not entry_lines:
            raise VerificationError("payment journal entry lines missing")
        debit_total = sum((line.debit_base for line in entry_lines), Decimal("0.00"))
        credit_total = sum((line.credit_base for line in entry_lines), Decimal("0.00"))
        if _quantize(debit_total) != _quantize(credit_total):
            raise VerificationError("payment journal entry not balanced")
        totals_by_account = {str(cash_account_id): Decimal("0.00"), str(ap_account_id): Decimal("0.00"), str(vendor_prepay_account_id): Decimal("0.00")}
        for line in entry_lines:
            account_id = str(line.account_id)
            if account_id in totals_by_account:
                totals_by_account[account_id] += _quantize(line.debit_base) - _quantize(line.credit_base)
        if totals_by_account[str(cash_account_id)] != Decimal("-250.00"):
            raise VerificationError("cash credit for payment incorrect")
        if totals_by_account[str(ap_account_id)] != Decimal("200.00"):
            raise VerificationError("AP debit for payment incorrect")
        if totals_by_account[str(vendor_prepay_account_id)] != Decimal("50.00"):
            raise VerificationError("vendor prepay asset incorrect")

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await _expect_error(
            client,
            "POST",
            f"/api/v1/payments/{payment_id}/post",
            409,
            "vendor_payment_already_posted",
            headers=headers_a,
        )
        async with session_maker() as session:
            payment_entries = await _fetch_entries(session, tenant_a_id, "vendor_payment", uuid.UUID(payment_id))
            if len(payment_entries) != 1:
                raise VerificationError("double-post created extra payment journal entries")

        print("TEST 8: period lock enforcement")
        lock = await _expect_status(
            client,
            "POST",
            "/api/v1/journals/period-locks",
            201,
            headers=headers_a,
            json={"start_date": today, "end_date": today},
        )
        lock_id = lock.get("id")

        locked_receipt = await _expect_status(
            client,
            "POST",
            f"/api/v1/customers/{customer_id}/receipts",
            201,
            headers=headers_a,
            json={
                "receipt_date": today,
                "amount_total": "10.00",
                "cash_account_id": str(cash_account_id),
            },
        )
        locked_receipt_id = locked_receipt.get("id")
        if not locked_receipt_id:
            raise VerificationError("locked receipt id missing")
        await _expect_error(
            client,
            "POST",
            f"/api/v1/receipts/{locked_receipt_id}/post",
            409,
            "accounting_period_locked",
            headers=headers_a,
        )

        locked_payment = await _expect_status(
            client,
            "POST",
            f"/api/v1/vendors/{vendor_id}/payments",
            201,
            headers=headers_a,
            json={
                "payment_date": today,
                "amount_total": "10.00",
                "cash_account_id": str(cash_account_id),
            },
        )
        locked_payment_id = locked_payment.get("id")
        if not locked_payment_id:
            raise VerificationError("locked payment id missing")
        await _expect_error(
            client,
            "POST",
            f"/api/v1/payments/{locked_payment_id}/post",
            409,
            "accounting_period_locked",
            headers=headers_a,
        )

        await _expect_error(
            client,
            "POST",
            f"/api/v1/receipts/{receipt_id}/reverse",
            409,
            "accounting_period_locked",
            headers=headers_a,
            json={"reason": "locked period reversal"},
        )
        await _expect_error(
            client,
            "POST",
            f"/api/v1/payments/{payment_id}/reverse",
            409,
            "accounting_period_locked",
            headers=headers_a,
            json={"reason": "locked period reversal"},
        )

        if lock_id:
            await _expect_status(
                client,
                "DELETE",
                f"/api/v1/journals/period-locks/{lock_id}",
                200,
                headers=headers_a,
            )

        print("TEST 9: reverse receipt")
        reversed_receipt = await _expect_status(
            client,
            "POST",
            f"/api/v1/receipts/{receipt_id}/reverse",
            200,
            headers=headers_a,
            json={"reason": "receipt reversal"},
        )
        if reversed_receipt.get("status") != "REVERSED":
            raise VerificationError("receipt did not reverse")
        reversal_entry_id = reversed_receipt.get("reversal_journal_entry_id")
        if not reversal_entry_id:
            raise VerificationError("receipt reversal journal entry missing")
        async with session_maker() as session:
            reversal_entries = await _fetch_reversal_entries(
                session, tenant_a_id, uuid.UUID(receipt_entry_id)
            )
            if len(reversal_entries) != 1:
                raise VerificationError("receipt reversal journal entry count incorrect")
            reversal_lines = await _fetch_entry_lines(
                session, tenant_a_id, uuid.UUID(reversal_entry_id)
            )
            debit_total = sum((line.debit_base for line in reversal_lines), Decimal("0.00"))
            credit_total = sum((line.credit_base for line in reversal_lines), Decimal("0.00"))
            if _quantize(debit_total) != _quantize(credit_total):
                raise VerificationError("receipt reversal journal entry not balanced")
        await _expect_error(
            client,
            "POST",
            f"/api/v1/receipts/{receipt_id}/reverse",
            409,
            "customer_receipt_already_reversed",
            headers=headers_a,
            json={"reason": "second reversal"},
        )

        print("TEST 10: reverse payment")
        reversed_payment = await _expect_status(
            client,
            "POST",
            f"/api/v1/payments/{payment_id}/reverse",
            200,
            headers=headers_a,
            json={"reason": "payment reversal"},
        )
        if reversed_payment.get("status") != "REVERSED":
            raise VerificationError("payment did not reverse")
        reversal_entry_id = reversed_payment.get("reversal_journal_entry_id")
        if not reversal_entry_id:
            raise VerificationError("payment reversal journal entry missing")
        async with session_maker() as session:
            reversal_entries = await _fetch_reversal_entries(
                session, tenant_a_id, uuid.UUID(payment_entry_id)
            )
            if len(reversal_entries) != 1:
                raise VerificationError("payment reversal journal entry count incorrect")
            reversal_lines = await _fetch_entry_lines(
                session, tenant_a_id, uuid.UUID(reversal_entry_id)
            )
            debit_total = sum((line.debit_base for line in reversal_lines), Decimal("0.00"))
            credit_total = sum((line.credit_base for line in reversal_lines), Decimal("0.00"))
            if _quantize(debit_total) != _quantize(credit_total):
                raise VerificationError("payment reversal journal entry not balanced")
        await _expect_error(
            client,
            "POST",
            f"/api/v1/payments/{payment_id}/reverse",
            409,
            "vendor_payment_already_reversed",
            headers=headers_a,
            json={"reason": "second reversal"},
        )

        print("TEST 11: tenant isolation")
        await _expect_error(
            client,
            "GET",
            f"/api/v1/receipts/{receipt_id}",
            404,
            "http_error",
            headers=headers_b,
        )
        await _expect_error(
            client,
            "GET",
            f"/api/v1/payments/{payment_id}",
            404,
            "http_error",
            headers=headers_b,
        )

    print("SPRINT 19 VERIFIED OK")


if __name__ == "__main__":
    asyncio.run(run())
