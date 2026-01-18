from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path


def _candidate_env_paths() -> list[Path]:
    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = backend_dir.parent
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
        print("verify_sprint6: env file not loaded; relying on process environment")
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


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


_prepare_environment()

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import engine
from app.initial_data import seed_tenant
from app.main import app
from app.models.tenant import Tenant


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


async def _create_seeded_tenant(session: AsyncSession) -> uuid.UUID:
    tenant = Tenant(
        name="Sprint 6 Verify",
        slug=f"sprint6-verify-{uuid.uuid4().hex[:8]}",
    )
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    await seed_tenant(session, tenant)
    return tenant.id


async def _expect_ok(client: AsyncClient, path: str, *, headers: dict | None = None) -> dict:
    response = await client.get(path, headers=headers)
    if response.status_code != 200:
        raise VerificationError(f"{path} returned {response.status_code}: {response.text}")
    return response.json()


async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        tenant_id = await _create_seeded_tenant(session)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await _expect_ok(client, "/health")
        if health.get("status") != "ok":
            raise VerificationError("health check did not return status=ok")

        db_health = await _expect_ok(client, "/health/db")
        if db_health.get("status") != "ok":
            raise VerificationError("db health check did not return status=ok")

        accounts = await _expect_ok(
            client,
            "/api/v1/accounts/",
            headers={"X-Tenant-Id": str(tenant_id)},
        )
        items = accounts.get("items")
        if not isinstance(items, list) or not items:
            raise VerificationError("accounts endpoint returned no items")

    print("Sprint 6 verification: OK")


def main() -> None:
    try:
        asyncio.run(run())
    except VerificationError as exc:
        print(f"Sprint 6 verification: FAILED - {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
