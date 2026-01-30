from __future__ import annotations

import asyncio
import os
import sys
import time
import uuid
from datetime import UTC, datetime, timedelta
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
        print("verify_sprint22: env file not loaded; relying on process environment")
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


async def _expect_unauthorized(
    client: AsyncClient,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    json: dict | None = None,
    params: dict | None = None,
) -> None:
    response = await client.request(method, path, headers=headers, json=json, params=params)
    if response.status_code not in {401, 403}:
        raise VerificationError(f"{method} {path} expected 401/403, got {response.status_code}: {response.text}")


async def _create_tenant_with_admin(
    session_maker: async_sessionmaker[AsyncSession],
    label: str,
) -> tuple[uuid.UUID, str]:
    async with session_maker() as session:
        tenant = Tenant(
            name=f"Sprint 22 {label}",
            slug=f"sprint22-{label}-{uuid.uuid4().hex[:8]}",
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
                "full_name": f"Sprint 22 {label} Admin",
                "role_id": admin_role.id,
            },
        )
        token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )
        return tenant_id, token


def _parse_iso_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise VerificationError(f"Invalid datetime format: {value}") from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


async def run() -> None:
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    _log("Waiting for database readiness")
    await _wait_for_db_ready(session_maker)
    await _check_migrations(session_maker)

    tenant_id, token = await _create_tenant_with_admin(session_maker, "portal-links")
    headers = _auth_headers(token, tenant_id)
    invalid_headers = {"Authorization": "Bearer invalid", "X-Tenant-Id": str(tenant_id)}

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    timeout = Timeout(connect=5.0, read=15.0, write=15.0, pool=5.0)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=timeout) as client:
        _log("TEST 1: create customer")
        customer = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=headers,
            json={"code": "PORTAL-22", "name": "Portal Share Customer"},
        )
        customer_id = customer.get("id")
        if not customer_id:
            raise VerificationError("customer id missing")

        _log("TEST 2: unauthenticated requests blocked")
        await _expect_unauthorized(
            client,
            "POST",
            "/api/v1/portal/link",
            headers=invalid_headers,
            json={"client_id": customer_id, "expires_in_hours": 1},
        )
        await _expect_unauthorized(
            client,
            "GET",
            f"/api/v1/portal/customers/{customer_id}/links",
            headers=invalid_headers,
        )

        _log("TEST 3: create portal link (expires_in_hours=1)")
        link = await _expect_status(
            client,
            "POST",
            "/api/v1/portal/link",
            201,
            headers=headers,
            json={"client_id": customer_id, "expires_in_hours": 1},
        )
        token_id = link.get("token_id")
        expires_at = link.get("expires_at")
        url = link.get("url")
        if not token_id or not expires_at or not url:
            raise VerificationError("portal link response missing token_id/url/expires_at")

        expires_at_dt = _parse_iso_datetime(expires_at)
        now = datetime.now(UTC)
        delta = abs((expires_at_dt - now) - timedelta(hours=1))
        if delta > timedelta(minutes=3):
            raise VerificationError(f"expires_at not ~1h: delta {delta}")

        raw_token = url.rstrip("/").split("/")[-1]
        if not raw_token:
            raise VerificationError("raw portal token missing")

        _log("TEST 4: list customer links")
        links = await _expect_status(
            client,
            "GET",
            f"/api/v1/portal/customers/{customer_id}/links",
            200,
            headers=headers,
        )
        if not any(item.get("token_id") == token_id for item in links):
            raise VerificationError("created token_id not found in list")

        _log("TEST 5: public portal summary before revoke")
        before = await client.get(f"/api/v1/portal/{raw_token}/summary")
        if before.status_code != 200:
            raise VerificationError(f"expected 200 before revoke, got {before.status_code}: {before.text}")

        _log("TEST 6: revoke portal link")
        await _expect_unauthorized(
            client,
            "POST",
            f"/api/v1/portal/links/{token_id}/revoke",
            headers=invalid_headers,
        )
        revoke = await _expect_status(
            client,
            "POST",
            f"/api/v1/portal/links/{token_id}/revoke",
            200,
            headers=headers,
        )
        if not revoke.get("revoked_at"):
            raise VerificationError("revoked_at missing after revoke")

        _log("TEST 7: revoked token invalid")
        invalid = await client.get(f"/api/v1/portal/{raw_token}/summary")
        if invalid.status_code != 404:
            raise VerificationError(f"expected 404 after revoke, got {invalid.status_code}")

    _log("PASS: Sprint 22 customer share links")


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
