from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from datetime import UTC, date, datetime, timedelta
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
        print("verify_sprint23: env file not loaded; relying on process environment")
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
from app.models.invoice import Invoice, InvoiceStatus  # noqa: E402
from app.models.role import Role  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.services import user_service  # noqa: E402


class VerificationError(RuntimeError):
    pass


START_TIME = time.monotonic()
EXPECTED_HEAD = "0022_sprint22_portal_links"


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
            name=f"Sprint 23 {label}",
            slug=f"sprint23-{label}-{uuid.uuid4().hex[:8]}",
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
                "full_name": f"Sprint 23 {label} Admin",
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


async def run() -> None:
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    _log("Waiting for database readiness")
    await _wait_for_db_ready(session_maker)
    await _check_migrations(session_maker)

    tenant_id, token = await _create_tenant_with_admin(session_maker, "portal-premium")
    headers = _auth_headers(token, tenant_id)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    timeout = Timeout(connect=5.0, read=15.0, write=15.0, pool=5.0)

    async with AsyncClient(transport=transport, base_url="http://test", timeout=timeout) as client:
        _log("TEST 1: create customers")
        customer_a = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=headers,
            json={"code": "PORTAL-23-A", "name": "Portal Customer A"},
        )
        customer_b = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=headers,
            json={"code": "PORTAL-23-B", "name": "Portal Customer B"},
        )

        customer_a_id = uuid.UUID(customer_a["id"])
        customer_b_id = uuid.UUID(customer_b["id"])

        _log("TEST 2: insert invoices with varied statuses")
        today = date.today()
        async with session_maker() as session:
            invoice_open = await _insert_invoice(
                session,
                tenant_id=tenant_id,
                customer_id=customer_a_id,
                status=InvoiceStatus.SENT,
                issue_date=today,
                due_date=today + timedelta(days=7),
                total_amount=Decimal("125.00"),
            )
            invoice_paid = await _insert_invoice(
                session,
                tenant_id=tenant_id,
                customer_id=customer_a_id,
                status=InvoiceStatus.PAID,
                issue_date=today - timedelta(days=10),
                due_date=today - timedelta(days=5),
                total_amount=Decimal("250.00"),
                notes="REF-PAID-001",
            )
            invoice_cancelled = await _insert_invoice(
                session,
                tenant_id=tenant_id,
                customer_id=customer_a_id,
                status=InvoiceStatus.CANCELLED,
                issue_date=today - timedelta(days=20),
                due_date=today - timedelta(days=15),
                total_amount=Decimal("75.00"),
            )
            invoice_overdue = await _insert_invoice(
                session,
                tenant_id=tenant_id,
                customer_id=customer_a_id,
                status=InvoiceStatus.OVERDUE,
                issue_date=today - timedelta(days=30),
                due_date=today - timedelta(days=25),
                total_amount=Decimal("300.00"),
            )
            _ = await _insert_invoice(
                session,
                tenant_id=tenant_id,
                customer_id=customer_b_id,
                status=InvoiceStatus.SENT,
                issue_date=today,
                due_date=today + timedelta(days=7),
                total_amount=Decimal("99.00"),
            )

        _log("TEST 3: create portal token for customer A")
        link = await _expect_status(
            client,
            "POST",
            "/api/v1/portal/link",
            201,
            headers=headers,
            json={"client_id": str(customer_a_id)},
        )
        portal_url = link.get("url") or ""
        raw_token = portal_url.rstrip("/").split("/")[-1]
        if not raw_token:
            raise VerificationError("portal token missing")

        _log("TEST 4: portal invoices all + isolation")
        all_resp = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/{raw_token}/invoices",
            200,
            params={"status": "all", "page": 1, "page_size": 10},
        )
        items = all_resp.get("invoices") or []
        if len(items) < 4:
            raise VerificationError("expected at least 4 invoices for customer A")
        if any(item.get("customer_id") == str(customer_b_id) for item in items):
            raise VerificationError("customer B invoice leaked into customer A portal")

        _log("TEST 5: status filters")
        paid_resp = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/{raw_token}/invoices",
            200,
            params={"status": "paid"},
        )
        if not all(item.get("status") == "PAID" for item in paid_resp.get("invoices") or []):
            raise VerificationError("paid filter returned non-paid invoices")

        overdue_resp = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/{raw_token}/invoices",
            200,
            params={"status": "overdue"},
        )
        if not any(item.get("status") == "OVERDUE" for item in overdue_resp.get("invoices") or []):
            raise VerificationError("overdue filter missing overdue invoice")

        open_resp = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/{raw_token}/invoices",
            200,
            params={"status": "open"},
        )
        if any(item.get("status") in {"PAID", "CANCELLED"} for item in open_resp.get("invoices") or []):
            raise VerificationError("open filter returned paid/cancelled invoices")

        _log("TEST 6: search by reference")
        search_resp = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/{raw_token}/invoices",
            200,
            params={"q": "REF-PAID-001"},
        )
        if not any(item.get("id") == str(invoice_paid.id) for item in search_resp.get("invoices") or []):
            raise VerificationError("search did not return matching invoice")

        _log("TEST 7: pagination sanity")
        page_one = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/{raw_token}/invoices",
            200,
            params={"status": "all", "page": 1, "page_size": 2, "sort": "newest"},
        )
        page_two = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/{raw_token}/invoices",
            200,
            params={"status": "all", "page": 2, "page_size": 2, "sort": "newest"},
        )
        if page_one.get("page") != 1 or page_two.get("page") != 2:
            raise VerificationError("pagination page values incorrect")
        if page_one.get("total", 0) < 4:
            raise VerificationError("pagination total too small")
        if not page_two.get("invoices"):
            raise VerificationError("pagination missing second page results")

    _log("PASS: Sprint 23 portal premium verifier")


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
