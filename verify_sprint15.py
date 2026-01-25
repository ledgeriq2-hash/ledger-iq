from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import UTC, datetime
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
        print("verify_sprint15: env file not loaded; relying on process environment")
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
from app.utils.ai_hashing import canonical_sha256


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
) -> tuple[uuid.UUID, str, uuid.UUID]:
    async with session_maker() as session:
        tenant = Tenant(
            name=f"Sprint 15 {label}",
            slug=f"sprint15-{label}-{uuid.uuid4().hex[:8]}",
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
                "full_name": f"Sprint 15 {label} Admin",
                "role_id": admin_role.id,
            },
        )
        token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )
        return tenant_id, token, admin_user.id


async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    tenant_id, token, admin_user_id = await _create_tenant_with_admin(session_maker, "primary")
    other_tenant_id, other_token, _ = await _create_tenant_with_admin(session_maker, "secondary")

    headers = _auth_headers(token, tenant_id)
    other_headers = _auth_headers(other_token, other_tenant_id)

    payload = {
        "forecast": {"currency": "USD", "points": [{"date": "2026-02-01", "value": 1200.0}]},
        "risk": {"overall": "low", "factors": [{"name": "seasonality", "score": 0.2}]},
    }
    create_payload = {
        "schema_version": "1.0",
        "run_meta": {
            "model_name": "ledgeriq-forecast-lstm",
            "model_version": "2026.01",
            "dataset_fingerprint": "fp-12345",
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": "verifier@ledgeriq.ai",
            "date_from": "2025-10-01",
            "date_to": "2025-12-31",
        },
        "payload": payload,
        "signature": None,
    }

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await _expect_status(
            client,
            "POST",
            "/api/v1/ai/runs",
            201,
            headers=headers,
            json=create_payload,
        )
        if created.get("status") != "approved":
            raise VerificationError("create run status mismatch")
        run_id = created.get("id")
        if not run_id:
            raise VerificationError("create run id missing")
        expected_hash = canonical_sha256(payload)
        if created.get("payload_hash") != expected_hash:
            raise VerificationError("payload_hash mismatch")
        if created.get("payload_json") != payload:
            raise VerificationError("payload_json mismatch")
        run_meta = created.get("run_meta") or {}
        if run_meta.get("scenario") != "baseline":
            raise VerificationError("scenario default mismatch")
        if run_meta.get("created_by") != "verifier@ledgeriq.ai":
            raise VerificationError("created_by mismatch")

        listed = await _expect_status(
            client,
            "GET",
            "/api/v1/ai/runs",
            200,
            headers=headers,
            params={"limit": 50, "offset": 0, "status": "approved"},
        )
        if not isinstance(listed, list) or not any(item.get("id") == run_id for item in listed):
            raise VerificationError("created run not found in list")

        fetched = await _expect_status(
            client,
            "GET",
            f"/api/v1/ai/runs/{run_id}",
            200,
            headers=headers,
        )
        if fetched.get("payload_hash") != expected_hash:
            raise VerificationError("get run payload_hash mismatch")
        if fetched.get("payload_json") != payload:
            raise VerificationError("get run payload_json mismatch")

        revoked = await _expect_status(
            client,
            "POST",
            f"/api/v1/ai/runs/{run_id}/revoke",
            200,
            headers=headers,
            json={"reason": "Sprint 15 revoke"},
        )
        if revoked.get("status") != "revoked":
            raise VerificationError("revoke status mismatch")
        if not revoked.get("revoked_at"):
            raise VerificationError("revoked_at missing")
        if revoked.get("revoke_reason") != "Sprint 15 revoke":
            raise VerificationError("revoke_reason mismatch")
        if revoked.get("revoked_by") != str(admin_user_id):
            raise VerificationError("revoked_by mismatch")

        await _expect_error(
            client,
            "POST",
            f"/api/v1/ai/runs/{run_id}/revoke",
            409,
            "ai_run_already_revoked",
            headers=headers,
            json={"reason": "Second revoke"},
        )

        await _expect_error(
            client,
            "GET",
            f"/api/v1/ai/runs/{run_id}",
            404,
            "ai_run_not_found",
            headers=other_headers,
        )

    print("OK")


if __name__ == "__main__":
    asyncio.run(run())
