
from __future__ import annotations

import asyncio
import calendar
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
        print("verify_sprint20: env file not loaded; relying on process environment")
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
            name=f"Sprint 20 {label}",
            slug=f"sprint20-{label}-{uuid.uuid4().hex[:8]}",
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
                "full_name": f"Sprint 20 {label} Admin",
                "role_id": admin_role.id,
            },
        )
        token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )
        return tenant_id, token


async def _set_base_currency(session: AsyncSession, tenant_id: uuid.UUID, currency: str) -> None:
    tenant = await session.scalar(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant:
        raise VerificationError("tenant not found for base currency update")
    settings = dict(tenant.settings_json) if isinstance(tenant.settings_json, dict) else {}
    settings["BASE_CURRENCY"] = currency.strip().upper()
    tenant.settings_json = settings
    session.add(tenant)
    await session.commit()


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


async def _get_account_by_code(session: AsyncSession, tenant_id: uuid.UUID, code: str) -> Account | None:
    result = await session.execute(
        select(Account).where(Account.tenant_id == tenant_id, Account.code == code)
    )
    return result.scalar_one_or_none()


async def _ensure_account(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    code: str,
    name: str,
    account_type: str,
    normal_balance: str,
) -> uuid.UUID:
    account = await _get_account_by_code(session, tenant_id, code)
    if account:
        return account.id
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
    await session.commit()
    return account.id


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
        .where(Account.tenant_id == tenant_id, Account.type == "EXPENSE")
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


def _base_totals_by_account(lines: list[JournalLine]) -> dict[str, dict[str, Decimal]]:
    totals: dict[str, dict[str, Decimal]] = {}
    for line in lines:
        key = str(line.account_id)
        bucket = totals.setdefault(key, {"debit": Decimal("0.00"), "credit": Decimal("0.00")})
        bucket["debit"] += _quantize(line.debit_base or 0)
        bucket["credit"] += _quantize(line.credit_base or 0)
    for bucket in totals.values():
        bucket["debit"] = _quantize(bucket["debit"])
        bucket["credit"] = _quantize(bucket["credit"])
    return totals


def _entry_base_totals(lines: list[JournalLine]) -> tuple[Decimal, Decimal]:
    debit_total = sum((_quantize(line.debit_base or 0) for line in lines), Decimal("0.00"))
    credit_total = sum((_quantize(line.credit_base or 0) for line in lines), Decimal("0.00"))
    return _quantize(debit_total), _quantize(credit_total)
async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    tenant_a_id, token_a = await _create_tenant_with_admin(session_maker, "tenant-a")
    tenant_b_id, token_b = await _create_tenant_with_admin(session_maker, "tenant-b")

    async with session_maker() as session:
        await _set_base_currency(session, tenant_a_id, "EGP")
        ar_account_id = await _ensure_account(
            session,
            tenant_a_id,
            code="1300",
            name="Accounts Receivable",
            account_type="ASSET",
            normal_balance="debit",
        )
        ap_account_id = await _ensure_account(
            session,
            tenant_a_id,
            code="2100",
            name="Accounts Payable",
            account_type="LIABILITY",
            normal_balance="credit",
        )
        output_vat_account_id = await _ensure_account(
            session,
            tenant_a_id,
            code="2210",
            name="Output VAT Payable",
            account_type="LIABILITY",
            normal_balance="credit",
        )
        input_vat_account_id = await _ensure_account(
            session,
            tenant_a_id,
            code="1410",
            name="Input VAT Recoverable",
            account_type="ASSET",
            normal_balance="debit",
        )
        customer_credit_account_id = await _ensure_account(
            session,
            tenant_a_id,
            code="2300",
            name="Customer Credits",
            account_type="LIABILITY",
            normal_balance="credit",
        )
        vendor_prepay_account_id = await _ensure_account(
            session,
            tenant_a_id,
            code="1500",
            name="Vendor Prepayments",
            account_type="ASSET",
            normal_balance="debit",
        )
        fx_gain_account_id = await _ensure_account(
            session,
            tenant_a_id,
            code="6101",
            name="FX Gain",
            account_type="INCOME",
            normal_balance="credit",
        )
        fx_loss_account_id = await _ensure_account(
            session,
            tenant_a_id,
            code="6102",
            name="FX Loss",
            account_type="EXPENSE",
            normal_balance="debit",
        )
        revenue_account_ids = await _get_or_create_revenue_accounts(session, tenant_a_id)
        expense_account_ids = await _get_or_create_expense_accounts(session, tenant_a_id)
        cash_account_id = await _get_cash_account_id(session, tenant_a_id)

        await _ensure_account_mapping(session, tenant_a_id, "AR_CONTROL", ar_account_id)
        await _ensure_account_mapping(session, tenant_a_id, "AP_CONTROL", ap_account_id)
        await _ensure_account_mapping(session, tenant_a_id, "OUTPUT_VAT", output_vat_account_id)
        await _ensure_account_mapping(session, tenant_a_id, "INPUT_VAT", input_vat_account_id)
        await _ensure_account_mapping(session, tenant_a_id, "CUSTOMER_CREDIT", customer_credit_account_id)
        await _ensure_account_mapping(session, tenant_a_id, "VENDOR_PREPAY", vendor_prepay_account_id)
        await _ensure_account_mapping(session, tenant_a_id, "FX_GAIN", fx_gain_account_id)
        await _ensure_account_mapping(session, tenant_a_id, "FX_LOSS", fx_loss_account_id)

    headers_a = _auth_headers(token_a, tenant_a_id)
    headers_b = _auth_headers(token_b, tenant_b_id)
    today_date = date.today()
    today = today_date.isoformat()
    period_id = f"{today_date.year}-{today_date.month:02d}"
    period_end = date(today_date.year, today_date.month, calendar.monthrange(today_date.year, today_date.month)[1])

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
                "name": "Sprint 20 Customer",
                "email": "customer20@example.com",
            },
        )
        customer_id = customer.get("id")
        if not customer_id:
            raise VerificationError("customer id missing")

        print("TEST 2: create vendor")
        vendor = await _expect_status(
            client,
            "POST",
            "/api/v1/vendors/",
            201,
            headers=headers_a,
            json={
                "name": "Sprint 20 Vendor",
                "email": "vendor20@example.com",
            },
        )
        vendor_id = vendor.get("id")
        if not vendor_id:
            raise VerificationError("vendor id missing")
        print("TEST 3: create draft sales invoice (no ledger impact)")
        draft_invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/customers/{customer_id}/sales-invoices",
            201,
            headers=headers_a,
            json={
                "invoice_date": today,
                "currency_code": "USD",
                "fx_rate": "30",
                "memo": "Sprint 20 invoice",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Consulting",
                        "quantity": "1",
                        "unit_price": "100.00",
                        "amount": "100.00",
                        "vat_rate": "0.14",
                        "vat_amount": "14.00",
                        "revenue_account_id": str(revenue_account_ids[0]),
                    }
                ],
            },
        )
        invoice_id = draft_invoice.get("id")
        if not invoice_id:
            raise VerificationError("draft invoice id missing")
        if draft_invoice.get("status") != "DRAFT":
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
            if entry_count:
                raise VerificationError("draft invoice created journal entry")

        print("TEST 4: post sales invoice with VAT + FX")
        posted_invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/post",
            200,
            headers=headers_a,
        )
        if posted_invoice.get("status") != "POSTED":
            raise VerificationError("invoice not posted")
        if not posted_invoice.get("invoice_no"):
            raise VerificationError("invoice number not assigned")
        if not posted_invoice.get("posting_journal_entry_id"):
            raise VerificationError("invoice posting journal entry missing")

        if _quantize(posted_invoice.get("vat_total")) != Decimal("14.00"):
            raise VerificationError("invoice vat_total incorrect")
        if _quantize(posted_invoice.get("base_subtotal")) != Decimal("3000.00"):
            raise VerificationError("invoice base_subtotal incorrect")
        if _quantize(posted_invoice.get("base_vat_total")) != Decimal("420.00"):
            raise VerificationError("invoice base_vat_total incorrect")
        if _quantize(posted_invoice.get("base_total")) != Decimal("3420.00"):
            raise VerificationError("invoice base_total incorrect")

        async with session_maker() as session:
            entries = await _fetch_entries(session, tenant_a_id, "sales_invoice", uuid.UUID(invoice_id))
            if len(entries) != 1:
                raise VerificationError("expected 1 sales invoice journal entry")
            lines = await _fetch_entry_lines(session, tenant_a_id, entries[0].id)
            debit_total, credit_total = _entry_base_totals(lines)
            if debit_total != credit_total:
                raise VerificationError("sales invoice journal entry not balanced")
            totals = _base_totals_by_account(lines)
            if totals[str(ar_account_id)]["debit"] != Decimal("3420.00"):
                raise VerificationError("AR debit incorrect for sales invoice")
            if totals[str(revenue_account_ids[0])]["credit"] != Decimal("3000.00"):
                raise VerificationError("revenue credit incorrect for sales invoice")
            if totals[str(output_vat_account_id)]["credit"] != Decimal("420.00"):
                raise VerificationError("output VAT credit incorrect for sales invoice")
        print("TEST 5: create draft purchase bill (no ledger impact)")
        draft_bill = await _expect_status(
            client,
            "POST",
            f"/api/v1/vendors/{vendor_id}/purchase-bills",
            201,
            headers=headers_a,
            json={
                "invoice_date": today,
                "currency_code": "USD",
                "fx_rate": "30",
                "memo": "Sprint 20 bill",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Supplies",
                        "quantity": "1",
                        "unit_price": "200.00",
                        "amount": "200.00",
                        "vat_rate": "0.14",
                        "vat_amount": "28.00",
                        "expense_account_id": str(expense_account_ids[0]),
                    }
                ],
            },
        )
        bill_id = draft_bill.get("id")
        if not bill_id:
            raise VerificationError("draft bill id missing")
        if draft_bill.get("status") != "DRAFT":
            raise VerificationError("draft bill status mismatch")

        async with session_maker() as session:
            entry_count = await session.scalar(
                select(func.count())
                .select_from(JournalEntry)
                .where(
                    JournalEntry.tenant_id == tenant_a_id,
                    JournalEntry.source_type == "purchase_invoice",
                    JournalEntry.source_id == uuid.UUID(bill_id),
                )
            )
            if entry_count:
                raise VerificationError("draft bill created journal entry")

        print("TEST 6: post purchase bill with VAT + FX")
        posted_bill = await _expect_status(
            client,
            "POST",
            f"/api/v1/purchase-bills/{bill_id}/post",
            200,
            headers=headers_a,
        )
        if posted_bill.get("status") != "POSTED":
            raise VerificationError("bill not posted")
        if not posted_bill.get("bill_no"):
            raise VerificationError("bill number not assigned")
        if not posted_bill.get("posting_journal_entry_id"):
            raise VerificationError("bill posting journal entry missing")

        if _quantize(posted_bill.get("vat_total")) != Decimal("28.00"):
            raise VerificationError("bill vat_total incorrect")
        if _quantize(posted_bill.get("base_subtotal")) != Decimal("6000.00"):
            raise VerificationError("bill base_subtotal incorrect")
        if _quantize(posted_bill.get("base_vat_total")) != Decimal("840.00"):
            raise VerificationError("bill base_vat_total incorrect")
        if _quantize(posted_bill.get("base_total")) != Decimal("6840.00"):
            raise VerificationError("bill base_total incorrect")

        async with session_maker() as session:
            entries = await _fetch_entries(session, tenant_a_id, "purchase_invoice", uuid.UUID(bill_id))
            if len(entries) != 1:
                raise VerificationError("expected 1 purchase bill journal entry")
            lines = await _fetch_entry_lines(session, tenant_a_id, entries[0].id)
            debit_total, credit_total = _entry_base_totals(lines)
            if debit_total != credit_total:
                raise VerificationError("purchase bill journal entry not balanced")
            totals = _base_totals_by_account(lines)
            if totals[str(expense_account_ids[0])]["debit"] != Decimal("6000.00"):
                raise VerificationError("expense debit incorrect for purchase bill")
            if totals[str(input_vat_account_id)]["debit"] != Decimal("840.00"):
                raise VerificationError("input VAT debit incorrect for purchase bill")
            if totals[str(ap_account_id)]["credit"] != Decimal("6840.00"):
                raise VerificationError("AP credit incorrect for purchase bill")
        print("TEST 7: create receipt draft, allocate, post")
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
                "fx_rate": "30",
            },
        )
        receipt_id = receipt.get("id")
        if not receipt_id:
            raise VerificationError("receipt id missing")

        async with session_maker() as session:
            entry_count = await session.scalar(
                select(func.count())
                .select_from(JournalEntry)
                .where(
                    JournalEntry.tenant_id == tenant_a_id,
                    JournalEntry.source_type == "customer_receipt",
                    JournalEntry.source_id == uuid.UUID(receipt_id),
                )
            )
            if entry_count:
                raise VerificationError("draft receipt created journal entry")

        await _expect_status(
            client,
            "POST",
            f"/api/v1/receipts/{receipt_id}/allocations",
            201,
            headers=headers_a,
            json={
                "sales_invoice_id": invoice_id,
                "amount": "114.00",
            },
        )

        posted_receipt = await _expect_status(
            client,
            "POST",
            f"/api/v1/receipts/{receipt_id}/post",
            200,
            headers=headers_a,
        )
        if posted_receipt.get("status") != "POSTED":
            raise VerificationError("receipt not posted")
        if _quantize(posted_receipt.get("base_amount_total")) != Decimal("3600.00"):
            raise VerificationError("receipt base amount total incorrect")

        async with session_maker() as session:
            entries = await _fetch_entries(session, tenant_a_id, "customer_receipt", uuid.UUID(receipt_id))
            if len(entries) != 1:
                raise VerificationError("expected 1 receipt journal entry")
            lines = await _fetch_entry_lines(session, tenant_a_id, entries[0].id)
            debit_total, credit_total = _entry_base_totals(lines)
            if debit_total != credit_total:
                raise VerificationError("receipt journal entry not balanced")
            totals = _base_totals_by_account(lines)
            if totals[str(cash_account_id)]["debit"] != Decimal("3600.00"):
                raise VerificationError("cash debit incorrect for receipt")
            if totals[str(ar_account_id)]["credit"] != Decimal("3420.00"):
                raise VerificationError("AR credit incorrect for receipt")
            if totals[str(customer_credit_account_id)]["credit"] != Decimal("180.00"):
                raise VerificationError("customer credit incorrect for receipt")

        await _expect_error(
            client,
            "POST",
            f"/api/v1/receipts/{receipt_id}/post",
            409,
            "customer_receipt_already_posted",
            headers=headers_a,
        )
        print("TEST 8: create vendor payment draft, allocate, post")
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
                "fx_rate": "30",
            },
        )
        payment_id = payment.get("id")
        if not payment_id:
            raise VerificationError("payment id missing")

        async with session_maker() as session:
            entry_count = await session.scalar(
                select(func.count())
                .select_from(JournalEntry)
                .where(
                    JournalEntry.tenant_id == tenant_a_id,
                    JournalEntry.source_type == "vendor_payment",
                    JournalEntry.source_id == uuid.UUID(payment_id),
                )
            )
            if entry_count:
                raise VerificationError("draft payment created journal entry")

        await _expect_status(
            client,
            "POST",
            f"/api/v1/payments/{payment_id}/allocations",
            201,
            headers=headers_a,
            json={
                "purchase_bill_id": bill_id,
                "amount": "228.00",
            },
        )

        posted_payment = await _expect_status(
            client,
            "POST",
            f"/api/v1/payments/{payment_id}/post",
            200,
            headers=headers_a,
        )
        if posted_payment.get("status") != "POSTED":
            raise VerificationError("payment not posted")
        if _quantize(posted_payment.get("base_amount_total")) != Decimal("7500.00"):
            raise VerificationError("payment base amount total incorrect")

        async with session_maker() as session:
            entries = await _fetch_entries(session, tenant_a_id, "vendor_payment", uuid.UUID(payment_id))
            if len(entries) != 1:
                raise VerificationError("expected 1 payment journal entry")
            lines = await _fetch_entry_lines(session, tenant_a_id, entries[0].id)
            debit_total, credit_total = _entry_base_totals(lines)
            if debit_total != credit_total:
                raise VerificationError("payment journal entry not balanced")
            totals = _base_totals_by_account(lines)
            if totals[str(cash_account_id)]["credit"] != Decimal("7500.00"):
                raise VerificationError("cash credit incorrect for payment")
            if totals[str(ap_account_id)]["debit"] != Decimal("6840.00"):
                raise VerificationError("AP debit incorrect for payment")
            if totals[str(vendor_prepay_account_id)]["debit"] != Decimal("660.00"):
                raise VerificationError("vendor prepay incorrect for payment")

        await _expect_error(
            client,
            "POST",
            f"/api/v1/payments/{payment_id}/post",
            409,
            "vendor_payment_already_posted",
            headers=headers_a,
        )
        print("TEST 9: create open FX invoices/bills")
        open_invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/customers/{customer_id}/sales-invoices",
            201,
            headers=headers_a,
            json={
                "invoice_date": today,
                "currency_code": "USD",
                "fx_rate": "30",
                "memo": "Open invoice",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Service B",
                        "quantity": "1",
                        "unit_price": "50.00",
                        "amount": "50.00",
                        "vat_rate": "0.14",
                        "vat_amount": "7.00",
                        "revenue_account_id": str(revenue_account_ids[1]),
                    }
                ],
            },
        )
        open_invoice_id = open_invoice.get("id")
        if not open_invoice_id:
            raise VerificationError("open invoice id missing")
        await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{open_invoice_id}/post",
            200,
            headers=headers_a,
        )

        open_bill = await _expect_status(
            client,
            "POST",
            f"/api/v1/vendors/{vendor_id}/purchase-bills",
            201,
            headers=headers_a,
            json={
                "invoice_date": today,
                "currency_code": "USD",
                "fx_rate": "30",
                "memo": "Open bill",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Service C",
                        "quantity": "1",
                        "unit_price": "40.00",
                        "amount": "40.00",
                        "vat_rate": "0.14",
                        "vat_amount": "5.60",
                        "expense_account_id": str(expense_account_ids[1]),
                    }
                ],
            },
        )
        open_bill_id = open_bill.get("id")
        if not open_bill_id:
            raise VerificationError("open bill id missing")
        await _expect_status(
            client,
            "POST",
            f"/api/v1/purchase-bills/{open_bill_id}/post",
            200,
            headers=headers_a,
        )
        print("TEST 10: FX revaluation run")
        reval = await _expect_status(
            client,
            "POST",
            "/api/v1/fx-revaluation/run",
            201,
            headers=headers_a,
            json={
                "period_id": period_id,
                "currency": "USD",
                "reval_fx_rate": "32",
            },
        )
        run_id = reval.get("id")
        if not run_id:
            raise VerificationError("revaluation run id missing")
        if not reval.get("posting_journal_entry_id"):
            raise VerificationError("revaluation posting journal entry missing")

        async with session_maker() as session:
            entries = await _fetch_entries(session, tenant_a_id, "fx_revaluation", uuid.UUID(run_id))
            if len(entries) != 1:
                raise VerificationError("expected 1 revaluation journal entry")
            lines = await _fetch_entry_lines(session, tenant_a_id, entries[0].id)
            debit_total, credit_total = _entry_base_totals(lines)
            if debit_total != credit_total:
                raise VerificationError("revaluation journal entry not balanced")
            totals = _base_totals_by_account(lines)
            if totals[str(ar_account_id)]["debit"] != Decimal("114.00"):
                raise VerificationError("AR revaluation debit incorrect")
            if totals[str(fx_gain_account_id)]["credit"] != Decimal("114.00"):
                raise VerificationError("FX gain credit incorrect")
            if totals[str(ap_account_id)]["credit"] != Decimal("91.20"):
                raise VerificationError("AP revaluation credit incorrect")
            if totals[str(fx_loss_account_id)]["debit"] != Decimal("91.20"):
                raise VerificationError("FX loss debit incorrect")

        await _expect_error(
            client,
            "POST",
            "/api/v1/fx-revaluation/run",
            409,
            "fx_revaluation_already_exists",
            headers=headers_a,
            json={
                "period_id": period_id,
                "currency": "USD",
                "reval_fx_rate": "32",
            },
        )

        print("TEST 11: period lock enforcement for revaluation")
        lock = await _expect_status(
            client,
            "POST",
            "/api/v1/journals/period-locks",
            201,
            headers=headers_a,
            json={"start_date": period_end.isoformat(), "end_date": period_end.isoformat()},
        )
        lock_id = lock.get("id")

        await _expect_error(
            client,
            "POST",
            "/api/v1/fx-revaluation/run",
            409,
            "accounting_period_locked",
            headers=headers_a,
            json={
                "period_id": period_id,
                "currency": "EUR",
                "reval_fx_rate": "32",
            },
        )

        if lock_id:
            await _expect_status(
                client,
                "DELETE",
                f"/api/v1/journals/period-locks/{lock_id}",
                200,
                headers=headers_a,
            )

        print("TEST 12: tenant isolation")
        await _expect_error(
            client,
            "GET",
            f"/api/v1/sales-invoices/{invoice_id}",
            404,
            "http_error",
            headers=headers_b,
        )

    print("SPRINT 20 VERIFIED OK")


if __name__ == "__main__":
    asyncio.run(run())
