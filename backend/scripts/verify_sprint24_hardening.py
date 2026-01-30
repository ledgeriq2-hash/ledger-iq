from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, urlunparse


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


def _running_in_docker() -> bool:
    return Path("/.dockerenv").exists() or os.environ.get("RUNNING_IN_DOCKER") == "1"


def _prepare_environment() -> None:
    loaded = _load_env_with_dotenv()
    if not loaded and not _load_env_fallback():
        print("verify_sprint24: env file not loaded; relying on process environment")
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("CSRF_ENABLED", "false")
    os.environ.setdefault("BILLING_ENABLED", "false")
    os.environ.setdefault("FEATURE_OPTIONAL_ROUTES", "true")
    os.environ.setdefault("JWT_SECRET_KEY", "dev-jwt-secret-key")
    os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "dev-jwt-refresh-secret-key")
    os.environ.setdefault("STRIPE_API_KEY", "sk_test_dummy")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
    default_host = "postgres" if _running_in_docker() else "localhost"
    os.environ.setdefault(
        "DATABASE_URL",
        f"postgresql+asyncpg://ledgeriq:ledgeriq_password@{default_host}:5432/ledgeriq",
    )

    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        parsed = urlparse(db_url)
        if _running_in_docker() and parsed.hostname in {"localhost", "127.0.0.1"}:
            hostname = "postgres"
            netloc = parsed.netloc
            if "@" in netloc:
                creds, _ = netloc.rsplit("@", 1)
                netloc = f"{creds}@{hostname}:{parsed.port or 5432}"
            else:
                netloc = f"{hostname}:{parsed.port or 5432}"
            os.environ["DATABASE_URL"] = urlunparse(parsed._replace(netloc=netloc))
        elif not _running_in_docker() and parsed.hostname in {"postgres", "db"}:
            hostname = "localhost"
            netloc = parsed.netloc
            if "@" in netloc:
                creds, _ = netloc.rsplit("@", 1)
                netloc = f"{creds}@{hostname}:{parsed.port or 5432}"
            else:
                netloc = f"{hostname}:{parsed.port or 5432}"
            os.environ["DATABASE_URL"] = urlunparse(parsed._replace(netloc=netloc))


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


_prepare_environment()

from httpx import ASGITransport, AsyncClient, Timeout  # noqa: E402
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.database import engine  # noqa: E402
from app.initial_data import seed_tenant  # noqa: E402
from app.main import app  # noqa: E402
from app.models.account import Account  # noqa: E402
from app.models.customer_receipt import CustomerReceipt, CustomerReceiptStatus  # noqa: E402
from app.models.customer_receipt_allocation import CustomerReceiptAllocation  # noqa: E402
from app.models.invoice import Invoice, InvoiceStatus  # noqa: E402
from app.models.product import Product, ProductStatus  # noqa: E402
from app.models.role import Role  # noqa: E402
from app.models.sales_invoice import SalesInvoice, SalesInvoiceStatus  # noqa: E402
from app.models.stock_move import StockMove, StockMoveDirection, StockMoveSourceType  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.models.unit import InventoryUnit  # noqa: E402
from app.services import user_service  # noqa: E402


class VerificationError(RuntimeError):
    pass


START_TIME = time.monotonic()
EXPECTED_HEAD = "0023_sprint24_hardening_indexes"


def _log(message: str) -> None:
    elapsed = time.monotonic() - START_TIME
    timestamp = datetime.now(UTC).isoformat()
    print(f"[{timestamp}] (+{elapsed:05.1f}s) {message}")


async def _wait_for_db_ready(session_maker: async_sessionmaker[AsyncSession]) -> None:
    deadline = time.monotonic() + 20
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            async with session_maker() as session:
                await session.execute(text("SELECT 1"))
            _log("Database connection ready")
            return
        except Exception as exc:
            last_error = str(exc)
            await asyncio.sleep(1.5)
    raise VerificationError(
        f"Database not ready after 20s. Ensure docker-compose is up. Last error: {last_error}"
    )


async def _check_migrations(session_maker: async_sessionmaker[AsyncSession]) -> None:
    _log("Checking alembic migration status")
    try:
        async with session_maker() as session:
            result = await session.execute(text("SELECT version_num FROM alembic_version"))
            rows = result.fetchall()
    except Exception as exc:
        raise VerificationError(
            "Database migrations are not up to date. Run: alembic upgrade head"
        ) from exc
    versions = {row[0] for row in rows if row and row[0]}
    if EXPECTED_HEAD not in versions:
        raise VerificationError(
            f"Database migrations are not up to date (expected {EXPECTED_HEAD}). Run: alembic upgrade head"
        )


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
    headers: dict[str, str] | None = None,
    json: dict | None = None,
    params: dict | None = None,
) -> dict | list:
    response = await client.request(method, path, headers=headers, json=json, params=params)
    if response.status_code != expected_status:
        raise VerificationError(f"{method} {path} returned {response.status_code}: {response.text}")
    return response.json() if response.text else {}


async def _create_tenant_with_admin(
    session_maker: async_sessionmaker[AsyncSession],
    label: str,
) -> tuple[uuid.UUID, str]:
    async with session_maker() as session:
        tenant = Tenant(
            name=f"Sprint 24 {label}",
            slug=f"sprint24-{label}-{uuid.uuid4().hex[:8]}",
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
                "full_name": f"Sprint 24 {label} Admin",
                "role_id": admin_role.id,
            },
        )
        token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )
        return tenant_id, token


async def _insert_invoice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    status: InvoiceStatus,
    issue_date: date,
    due_date: date | None,
    total_amount: Decimal,
    notes: str | None = None,
) -> Invoice:
    invoice = Invoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        issue_date=issue_date,
        due_date=due_date,
        status=status,
        currency="USD",
        total_amount=total_amount,
        notes=notes,
    )
    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)
    return invoice


async def _insert_sales_invoice(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    invoice_date: date,
    due_date: date | None,
    total: Decimal,
) -> SalesInvoice:
    invoice = SalesInvoice(
        tenant_id=tenant_id,
        customer_id=customer_id,
        invoice_date=invoice_date,
        due_date=due_date,
        currency_code="USD",
        status=SalesInvoiceStatus.POSTED,
        subtotal=total,
        vat_total=Decimal("0.00"),
        total=total,
        total_amount=total,
        base_subtotal=total,
        base_vat_total=Decimal("0.00"),
        base_total=total,
    )
    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)
    return invoice


async def _get_cash_account_id(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    result = await session.execute(select(Account.id).where(Account.tenant_id == tenant_id).order_by(Account.code.asc()))
    account_id = result.scalars().first()
    if not account_id:
        raise VerificationError("No accounts found for tenant")
    return account_id


async def _insert_receipt_with_allocation(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    sales_invoice_id: uuid.UUID,
    cash_account_id: uuid.UUID,
    amount: Decimal,
) -> tuple[CustomerReceipt, CustomerReceiptAllocation]:
    receipt = CustomerReceipt(
        tenant_id=tenant_id,
        customer_id=customer_id,
        receipt_date=date.today(),
        currency_code="USD",
        amount_total=amount,
        base_amount_total=amount,
        cash_account_id=cash_account_id,
        status=CustomerReceiptStatus.DRAFT,
    )
    session.add(receipt)
    await session.commit()
    await session.refresh(receipt)

    allocation = CustomerReceiptAllocation(
        tenant_id=tenant_id,
        receipt_id=receipt.id,
        sales_invoice_id=sales_invoice_id,
        amount=amount,
    )
    session.add(allocation)
    await session.commit()
    await session.refresh(allocation)
    return receipt, allocation


async def _insert_stock_move(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    product_id: uuid.UUID,
    unit_id: uuid.UUID,
) -> StockMove:
    move = StockMove(
        tenant_id=tenant_id,
        product_id=product_id,
        unit_id=unit_id,
        quantity=Decimal("1.000000"),
        base_quantity=Decimal("1.000000"),
        source_type=StockMoveSourceType.PURCHASE,
        source_id=uuid.uuid4(),
        posted_at=datetime.now(UTC),
        reversed_stock_move_id=None,
        move_date=date.today(),
        direction=StockMoveDirection.IN,
        quantity_base=Decimal("1.00"),
        quantity_original=Decimal("1.00"),
        reference_type="purchase",
        reference_id=uuid.uuid4(),
    )
    session.add(move)
    await session.commit()
    await session.refresh(move)
    return move


async def _insert_unit_and_product(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    label: str,
) -> tuple[InventoryUnit, Product]:
    unit = InventoryUnit(
        tenant_id=tenant_id,
        code=f"UNIT-{label}",
        name=f"Unit {label}",
        ratio_to_base=Decimal("1.000000"),
        is_base=True,
    )
    session.add(unit)
    await session.commit()
    await session.refresh(unit)

    product = Product(
        tenant_id=tenant_id,
        code=f"PROD-{label}",
        name=f"Product {label}",
        status=ProductStatus.ACTIVE,
        is_active=True,
        base_unit_id=unit.id,
        unit_price=Decimal("1.00"),
        cost_price=Decimal("1.00"),
        stock_quantity=Decimal("0.00"),
        is_service=False,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return unit, product


async def run() -> None:
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    _log("Waiting for database readiness")
    await _wait_for_db_ready(session_maker)
    await _check_migrations(session_maker)

    tenant_a_id, token_a = await _create_tenant_with_admin(session_maker, "tenant-a")
    tenant_b_id, token_b = await _create_tenant_with_admin(session_maker, "tenant-b")
    headers_a = _auth_headers(token_a, tenant_a_id)
    headers_b = _auth_headers(token_b, tenant_b_id)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    timeout = Timeout(connect=5.0, read=15.0, write=15.0, pool=5.0)

    async with AsyncClient(transport=transport, base_url="http://test", timeout=timeout) as client:
        _log("TEST 1: create customers")
        customer_a = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=headers_a,
            json={"code": "HARD-A", "name": "Hardening A"},
        )
        customer_b = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=headers_b,
            json={"code": "HARD-B", "name": "Hardening B"},
        )
        customer_a_id = uuid.UUID(customer_a["id"])
        customer_b_id = uuid.UUID(customer_b["id"])

        _log("TEST 2: insert invoices per tenant")
        async with session_maker() as session:
            invoice_a = await _insert_invoice(
                session,
                tenant_id=tenant_a_id,
                customer_id=customer_a_id,
                status=InvoiceStatus.POSTED,
                issue_date=date.today(),
                due_date=date.today() + timedelta(days=7),
                total_amount=Decimal("50.00"),
                notes="TENANT-A-INV",
            )
            invoice_b = await _insert_invoice(
                session,
                tenant_id=tenant_b_id,
                customer_id=customer_b_id,
                status=InvoiceStatus.POSTED,
                issue_date=date.today(),
                due_date=date.today() + timedelta(days=7),
                total_amount=Decimal("60.00"),
                notes="TENANT-B-INV",
            )

        _log("TEST 3: list invoices isolated")
        list_a = await _expect_status(
            client,
            "GET",
            "/api/v1/invoices/",
            200,
            headers=headers_a,
            params={"page": 1, "page_size": 50},
        )
        ids_a = {item.get("id") for item in list_a.get("items", [])}
        if str(invoice_b.id) in ids_a:
            raise VerificationError("Tenant B invoice leaked into Tenant A list")

        list_b = await _expect_status(
            client,
            "GET",
            "/api/v1/invoices/",
            200,
            headers=headers_b,
            params={"page": 1, "page_size": 50},
        )
        ids_b = {item.get("id") for item in list_b.get("items", [])}
        if str(invoice_a.id) in ids_b:
            raise VerificationError("Tenant A invoice leaked into Tenant B list")

        _log("TEST 4: portal invoice search isolated")
        link = await _expect_status(
            client,
            "POST",
            "/api/v1/portal/link",
            201,
            headers=headers_a,
            json={"client_id": str(customer_a_id)},
        )
        portal_url = link.get("url") or ""
        raw_token = portal_url.rstrip("/").split("/")[-1]
        if not raw_token:
            raise VerificationError("portal token missing")

        search_a = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/{raw_token}/invoices",
            200,
            params={"q": "TENANT-A-INV"},
        )
        if not any(item.get("id") == str(invoice_a.id) for item in search_a.get("invoices", [])):
            raise VerificationError("Portal search missing tenant A invoice")

        search_b = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/{raw_token}/invoices",
            200,
            params={"q": "TENANT-B-INV"},
        )
        if any(item.get("id") == str(invoice_b.id) for item in search_b.get("invoices", [])):
            raise VerificationError("Portal search leaked tenant B invoice")

        _log("TEST 5: payments list isolated")
        payment_a = await _expect_status(
            client,
            "POST",
            "/api/v1/payments/",
            201,
            headers=headers_a,
            json={"customer_id": str(customer_a_id), "amount": "10.00", "method": "cash", "reference": "A"},
        )
        payment_b = await _expect_status(
            client,
            "POST",
            "/api/v1/payments/",
            201,
            headers=headers_b,
            json={"customer_id": str(customer_b_id), "amount": "12.00", "method": "cash", "reference": "B"},
        )
        payments_a = await _expect_status(
            client,
            "GET",
            "/api/v1/payments/",
            200,
            headers=headers_a,
            params={"page": 1, "page_size": 50},
        )
        payment_ids_a = {item.get("id") for item in payments_a.get("items", [])}
        if payment_b.get("id") in payment_ids_a:
            raise VerificationError("Tenant B payment leaked into Tenant A list")

        _log("TEST 6: allocations list isolated")
        async with session_maker() as session:
            cash_account_a = await _get_cash_account_id(session, tenant_a_id)
            cash_account_b = await _get_cash_account_id(session, tenant_b_id)
            sales_a = await _insert_sales_invoice(
                session,
                tenant_id=tenant_a_id,
                customer_id=customer_a_id,
                invoice_date=date.today(),
                due_date=date.today() + timedelta(days=7),
                total=Decimal("25.00"),
            )
            sales_b = await _insert_sales_invoice(
                session,
                tenant_id=tenant_b_id,
                customer_id=customer_b_id,
                invoice_date=date.today(),
                due_date=date.today() + timedelta(days=7),
                total=Decimal("35.00"),
            )
            receipt_a, allocation_a = await _insert_receipt_with_allocation(
                session,
                tenant_id=tenant_a_id,
                customer_id=customer_a_id,
                sales_invoice_id=sales_a.id,
                cash_account_id=cash_account_a,
                amount=Decimal("10.00"),
            )
            receipt_b, _ = await _insert_receipt_with_allocation(
                session,
                tenant_id=tenant_b_id,
                customer_id=customer_b_id,
                sales_invoice_id=sales_b.id,
                cash_account_id=cash_account_b,
                amount=Decimal("12.00"),
            )

        alloc_a = await _expect_status(
            client,
            "GET",
            f"/api/v1/receipts/{receipt_a.id}/allocations",
            200,
            headers=headers_a,
        )
        if not any(item.get("id") == str(allocation_a.id) for item in alloc_a):
            raise VerificationError("Tenant A allocation missing from list")

        cross_alloc = await client.get(
            f"/api/v1/receipts/{receipt_a.id}/allocations",
            headers=headers_b,
        )
        if cross_alloc.status_code != 404:
            raise VerificationError("Cross-tenant receipt allocations should 404")

        _log("TEST 7: stock ledger isolation")
        async with session_maker() as session:
            unit_a, product_a = await _insert_unit_and_product(session, tenant_id=tenant_a_id, label="A")
            unit_b, product_b = await _insert_unit_and_product(session, tenant_id=tenant_b_id, label="B")
            move_a = await _insert_stock_move(
                session,
                tenant_id=tenant_a_id,
                product_id=product_a.id,
                unit_id=unit_a.id,
            )
            _ = await _insert_stock_move(
                session,
                tenant_id=tenant_b_id,
                product_id=product_b.id,
                unit_id=unit_b.id,
            )

        ledger_a = await _expect_status(
            client,
            "GET",
            "/api/v1/stock/ledger",
            200,
            headers=headers_a,
            params={"page": 1, "page_size": 50},
        )
        ledger_items = ledger_a.get("items", [])
        if not any(item.get("id") == str(move_a.id) for item in ledger_items):
            raise VerificationError("Tenant A stock move missing from ledger")
        if any(item.get("product_id") == str(product_b.id) for item in ledger_items):
            raise VerificationError("Tenant B stock move leaked into Tenant A ledger")

        _log("TEST 8: portal link list isolated")
        links_a = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/customers/{customer_a_id}/links",
            200,
            headers=headers_a,
        )
        token_ids_a = {item.get("token_id") for item in links_a}
        if link.get("token_id") not in token_ids_a:
            raise VerificationError("Portal links missing for tenant A")

        links_b = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/customers/{customer_a_id}/links",
            200,
            headers=headers_b,
        )
        if any(item.get("token_id") == link.get("token_id") for item in links_b):
            raise VerificationError("Portal link leaked to tenant B")

    _log("PASS: Sprint 24 hardening verifier")


def main() -> int:
    try:
        asyncio.run(run())
        return 0
    except VerificationError as exc:
        print(f"FAIL: {exc}")
        return 1
    except Exception as exc:
        print(f"FAIL: unexpected error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
