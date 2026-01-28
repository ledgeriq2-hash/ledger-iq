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
        print("verify_sprint21: env file not loaded; relying on process environment")
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
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.database import engine  # noqa: E402
from app.initial_data import seed_tenant  # noqa: E402
from app.main import app  # noqa: E402
from app.models.account import Account  # noqa: E402
from app.models.account_mapping import AccountMapping  # noqa: E402
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
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        if detail:
            lines = [line.strip() for line in detail.splitlines() if line.strip()]
            detail = lines[-1] if lines else ""
        hint = ""
        if "stock_move_source_type" in detail or "DatatypeMismatch" in detail:
            hint = " (enum cast issue likely in 0021_inventory_stock_ledger.py)"
        message = "alembic upgrade head failed"
        if detail:
            message = f"{message}: {detail}"
        raise VerificationError(f"{message}{hint}") from exc


async def _get_role(session: AsyncSession, tenant_id: uuid.UUID, name: str) -> Role:
    result = await session.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name == name))
    role = result.scalar_one_or_none()
    if not role:
        raise VerificationError(f"role not found: {name}")
    return role


def _auth_headers(token: str, tenant_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-Id": str(tenant_id)}


def _quantize(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.000001"))


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
            name=f"Sprint 21 {label}",
            slug=f"sprint21-{label}-{uuid.uuid4().hex[:8]}",
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
                "full_name": f"Sprint 21 {label} Admin",
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


async def _get_or_create_revenue_accounts(session: AsyncSession, tenant_id: uuid.UUID) -> list[uuid.UUID]:
    result = await session.execute(
        select(Account)
        .where(Account.tenant_id == tenant_id, Account.type.in_(["INCOME", "REVENUE"]))
        .order_by(Account.code.asc())
    )
    accounts = list(result.scalars().all())
    if len(accounts) >= 1:
        return [accounts[0].id]

    existing_codes = {acct.code for acct in accounts}
    code = "4010"
    while code in existing_codes:
        code = str(int(code) + 10)
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
    await session.commit()
    await session.refresh(account)
    return [account.id]


async def _get_or_create_expense_account(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    result = await session.execute(
        select(Account)
        .where(Account.tenant_id == tenant_id, Account.type.in_(["EXPENSE", "EXPENSES"]))
        .order_by(Account.code.asc())
    )
    account = result.scalars().first()
    if account:
        return account.id

    account = Account(
        tenant_id=tenant_id,
        code="5010",
        name="Expense 5010",
        type="EXPENSE",
        normal_balance="debit",
        is_system=False,
        is_active=True,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account.id


async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    tenant_a_id, token_a = await _create_tenant_with_admin(session_maker, "tenant-a")
    tenant_b_id, token_b = await _create_tenant_with_admin(session_maker, "tenant-b")

    async with session_maker() as session:
        _ = await _get_ap_control_account_id(session, tenant_a_id)
        _ = await _get_ar_control_account_id(session, tenant_a_id)
        expense_account_id = await _get_or_create_expense_account(session, tenant_a_id)
        revenue_account_id = (await _get_or_create_revenue_accounts(session, tenant_a_id))[0]

    headers_a = _auth_headers(token_a, tenant_a_id)
    headers_b = _auth_headers(token_b, tenant_b_id)
    today = date.today().isoformat()

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("TEST 1: create inventory unit")
        unit = await _expect_status(
            client,
            "POST",
            "/api/v1/inventory-units/",
            201,
            headers=headers_a,
            json={"code": "PCS", "name": "Pieces", "ratio_to_base": "1"},
        )
        unit_id = unit.get("id")
        if not unit_id:
            raise VerificationError("inventory unit id missing")

        print("TEST 2: create product")
        product = await _expect_status(
            client,
            "POST",
            "/api/v1/products/",
            201,
            headers=headers_a,
            json={
                "name": "Widget",
                "base_unit_id": unit_id,
                "is_active": True,
            },
        )
        product_id = product.get("id")
        if not product_id:
            raise VerificationError("product id missing")
        if not product.get("code", "").startswith("PROD-"):
            raise VerificationError("product code not generated")

        print("TEST 3: create vendor & draft purchase bill (no stock)")
        vendor = await _expect_status(
            client,
            "POST",
            "/api/v1/vendors/",
            201,
            headers=headers_a,
            json={"code": "VEND-21", "name": "Sprint 21 Vendor"},
        )
        vendor_id = vendor.get("id")
        if not vendor_id:
            raise VerificationError("vendor id missing")

        draft_bill = await _expect_status(
            client,
            "POST",
            f"/api/v1/vendors/{vendor_id}/purchase-bills",
            201,
            headers=headers_a,
            json={
                "bill_no": None,
                "invoice_date": today,
                "currency_code": "USD",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Stock purchase",
                        "product_id": product_id,
                        "unit_id": unit_id,
                        "quantity": "10",
                        "unit_price": "5.00",
                        "amount": "50.00",
                        "expense_account_id": str(expense_account_id),
                    }
                ],
            },
        )
        bill_id = draft_bill.get("id")
        if not bill_id:
            raise VerificationError("purchase bill id missing")

        balance = await _expect_status(
            client,
            "GET",
            "/api/v1/stock/balance",
            200,
            headers=headers_a,
            params={"product_id": product_id},
        )
        if _quantize(balance.get("base_quantity")) != Decimal("0.000000"):
            raise VerificationError("draft purchase bill affected stock")

        print("TEST 4: post purchase bill -> stock IN")
        posted_bill = await _expect_status(
            client,
            "POST",
            f"/api/v1/purchase-bills/{bill_id}/post",
            200,
            headers=headers_a,
        )
        if posted_bill.get("status") != "POSTED":
            raise VerificationError("purchase bill did not post")

        balance = await _expect_status(
            client,
            "GET",
            "/api/v1/stock/balance",
            200,
            headers=headers_a,
            params={"product_id": product_id},
        )
        if _quantize(balance.get("base_quantity")) != Decimal("10.000000"):
            raise VerificationError("stock balance not updated after purchase bill")

        ledger = await _expect_status(
            client,
            "GET",
            "/api/v1/stock/ledger",
            200,
            headers=headers_a,
            params={"product_id": product_id},
        )
        items = ledger.get("items") or []
        if not items:
            raise VerificationError("stock ledger missing entries after purchase bill")
        if not any(item.get("source_type") == "PURCHASE" for item in items):
            raise VerificationError("stock ledger missing PURCHASE entry")

        print("TEST 5: create customer & draft sales invoice (no stock)")
        customer = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=headers_a,
            json={"name": "Sprint 21 Customer", "email": "customer21@example.com"},
        )
        customer_id = customer.get("id")
        if not customer_id:
            raise VerificationError("customer id missing")

        draft_invoice = await _expect_status(
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
                        "description": "Stock sale",
                        "product_id": product_id,
                        "unit_id": unit_id,
                        "quantity": "4",
                        "unit_price": "12.00",
                        "amount": "48.00",
                        "revenue_account_id": str(revenue_account_id),
                    }
                ],
            },
        )
        invoice_id = draft_invoice.get("id")
        if not invoice_id:
            raise VerificationError("sales invoice id missing")

        balance = await _expect_status(
            client,
            "GET",
            "/api/v1/stock/balance",
            200,
            headers=headers_a,
            params={"product_id": product_id},
        )
        if _quantize(balance.get("base_quantity")) != Decimal("10.000000"):
            raise VerificationError("draft sales invoice affected stock")

        print("TEST 6: post sales invoice -> stock OUT")
        posted_invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/post",
            200,
            headers=headers_a,
        )
        if posted_invoice.get("status") != "POSTED":
            raise VerificationError("sales invoice did not post")

        balance = await _expect_status(
            client,
            "GET",
            "/api/v1/stock/balance",
            200,
            headers=headers_a,
            params={"product_id": product_id},
        )
        if _quantize(balance.get("base_quantity")) != Decimal("6.000000"):
            raise VerificationError("stock balance not updated after sales invoice")

        print("TEST 7: prevent negative stock")
        over_invoice = await _expect_status(
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
                        "description": "Over sale",
                        "product_id": product_id,
                        "unit_id": unit_id,
                        "quantity": "20",
                        "unit_price": "12.00",
                        "amount": "240.00",
                        "revenue_account_id": str(revenue_account_id),
                    }
                ],
            },
        )
        over_invoice_id = over_invoice.get("id")
        await _expect_error(
            client,
            "POST",
            f"/api/v1/sales-invoices/{over_invoice_id}/post",
            409,
            "insufficient_stock",
            headers=headers_a,
        )

        print("TEST 8: reverse sales invoice -> stock restored")
        reversed_invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/reverse",
            200,
            headers=headers_a,
            json={"reason": "Sprint 21 reversal"},
        )
        if reversed_invoice.get("status") != "REVERSED":
            raise VerificationError("sales invoice did not reverse")

        balance = await _expect_status(
            client,
            "GET",
            "/api/v1/stock/balance",
            200,
            headers=headers_a,
            params={"product_id": product_id},
        )
        if _quantize(balance.get("base_quantity")) != Decimal("10.000000"):
            raise VerificationError("stock balance not restored after reversal")

        print("TEST 9: period lock enforcement")
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
                        "description": "Locked sale",
                        "product_id": product_id,
                        "unit_id": unit_id,
                        "quantity": "1",
                        "unit_price": "12.00",
                        "amount": "12.00",
                        "revenue_account_id": str(revenue_account_id),
                    }
                ],
            },
        )
        locked_invoice_id = locked_invoice.get("id")
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

        print("TEST 10: tenant isolation")
        await _expect_error(
            client,
            "GET",
            "/api/v1/stock/balance",
            404,
            "product_not_found",
            headers=headers_b,
            params={"product_id": product_id},
        )

    print("SPRINT 21 VERIFIED OK")


def main() -> None:
    try:
        asyncio.run(run())
    except VerificationError as exc:
        print(f"Sprint 21 inventory stock ledger verification: FAILED - {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
