from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
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
        print("verify_sprint11_customers: env file not loaded; relying on process environment")
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
            name="Sprint 11 Customers",
            slug=f"sprint11-customers-{uuid.uuid4().hex[:8]}",
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

    admin_headers = _auth_headers(admin_token, tenant_id)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "code": "CUST-1101",
            "name": "Sprint 11 Customer",
            "currency_code": "USD",
            "payment_terms_days": 15,
        }
        created = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=admin_headers,
            json=payload,
        )
        customer_id = created.get("id")
        if not customer_id:
            raise VerificationError("customer id missing on create")
        if created.get("currency_code") != "USD":
            raise VerificationError("customer currency_code mismatch")
        if created.get("payment_terms_days") != 15:
            raise VerificationError("customer payment_terms_days mismatch")

        fetched = await _expect_status(
            client,
            "GET",
            f"/api/v1/customers/{customer_id}",
            200,
            headers=admin_headers,
        )
        if fetched.get("code") != payload["code"]:
            raise VerificationError("customer code mismatch")
        if fetched.get("name") != payload["name"]:
            raise VerificationError("customer name mismatch")

        listing = await _expect_status(
            client,
            "GET",
            "/api/v1/customers/",
            200,
            headers=admin_headers,
        )
        items = listing.get("items") or []
        if not isinstance(items, list) or not items:
            raise VerificationError("customer list missing items")
        if not any(item.get("id") == customer_id for item in items):
            raise VerificationError("customer list does not include created customer")

        updated = await _expect_status(
            client,
            "PATCH",
            f"/api/v1/customers/{customer_id}",
            200,
            headers=admin_headers,
            json={
                "currency_code": "EUR",
                "payment_terms_days": 30,
                "status": "INACTIVE",
            },
        )
        if updated.get("currency_code") != "EUR":
            raise VerificationError("customer currency_code not updated")
        if updated.get("payment_terms_days") != 30:
            raise VerificationError("customer payment_terms_days not updated")
        if updated.get("status") != "INACTIVE":
            raise VerificationError("customer status not updated")

        duplicate_resp = await client.post(
            "/api/v1/customers/",
            headers=admin_headers,
            json={
                "code": payload["code"],
                "name": "Duplicate Customer",
            },
        )
        if duplicate_resp.status_code != 409:
            raise VerificationError("duplicate customer code did not fail with 409")
        if duplicate_resp.json().get("code") != "customer_code_exists":
            raise VerificationError("duplicate customer error code mismatch")

    print("Sprint 11 customers verification: OK")


def main() -> None:
    try:
        asyncio.run(run())
    except VerificationError as exc:
        print(f"Sprint 11 customers verification: FAILED - {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
