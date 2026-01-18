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
        print("verify_sprint8: env file not loaded; relying on process environment")
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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import create_access_token
from app.database import engine
from app.initial_data import seed_tenant
from app.main import app
from app.models.account import Account
from app.models.role import Role
from app.models.tenant import Tenant
from app.schemas.journals import JournalLineCreate
from app.services import user_service
from app.services.ledger_service import LedgerService


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
            name="Sprint 8 Verify",
            slug=f"sprint8-verify-{uuid.uuid4().hex[:8]}",
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        tenant_id = tenant.id

        await seed_tenant(session, tenant)

        admin_role = await _get_role(session, tenant_id, "ADMIN")
        viewer_role = await _get_role(session, tenant_id, "VIEWER")
        accountant_role = await _get_role(session, tenant_id, "ACCOUNTANT")

        admin_user = await user_service.create_user(
            session,
            tenant_id,
            {
                "email": f"admin-{tenant.slug}@example.com",
                "password": "Test1234",
                "full_name": "Sprint 8 Admin",
                "role_id": admin_role.id,
            },
        )
        viewer_user = await user_service.create_user(
            session,
            tenant_id,
            {
                "email": f"viewer-{tenant.slug}@example.com",
                "password": "Test1234",
                "full_name": "Sprint 8 Viewer",
                "role_id": viewer_role.id,
            },
        )
        accountant_user = await user_service.create_user(
            session,
            tenant_id,
            {
                "email": f"accountant-{tenant.slug}@example.com",
                "password": "Test1234",
                "full_name": "Sprint 8 Accountant",
                "role_id": accountant_role.id,
            },
        )

        admin_token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )
        viewer_token = create_access_token(
            str(viewer_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )
        accountant_token = create_access_token(
            str(accountant_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )

        accounts_result = await session.execute(
            select(Account).where(Account.tenant_id == tenant_id).order_by(Account.code.asc())
        )
        accounts = accounts_result.scalars().all()
        if len(accounts) < 2:
            raise VerificationError("expected at least two accounts for journal lines")

        debit_account_id = accounts[0].id
        credit_account_id = accounts[1].id

        service = LedgerService(session=session, tenant_id=tenant_id, actor_id=admin_user.id)
        entry = await service.create_manual_entry(
            entry_date=date.today(),
            base_currency="USD",
            memo="Sprint 8 verify entry",
            source_type="manual",
            source_id=None,
            lines=[
                JournalLineCreate(
                    account_id=debit_account_id,
                    debit_amount=Decimal("100.00"),
                    credit_amount=Decimal("0.00"),
                    line_currency="USD",
                ),
                JournalLineCreate(
                    account_id=credit_account_id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=Decimal("100.00"),
                    line_currency="USD",
                ),
            ],
        )
        line_ids = [line.id for line in entry.ledger_lines]
        if len(line_ids) < 2:
            raise VerificationError("expected two journal lines")

    admin_headers = _auth_headers(admin_token, tenant_id)
    viewer_headers = _auth_headers(viewer_token, tenant_id)
    accountant_headers = _auth_headers(accountant_token, tenant_id)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        viewer_resp = await client.post(
            "/api/v1/dimensions/",
            headers=viewer_headers,
            json={"key": "blocked", "name": "Blocked"},
        )
        if viewer_resp.status_code != 403:
            raise VerificationError("viewer managed dimensions unexpectedly")

        accountant_dimension = await _expect_status(
            client,
            "POST",
            "/api/v1/dimensions/",
            201,
            headers=accountant_headers,
            json={"key": "project", "name": "Project"},
        )
        if accountant_dimension.get("key") != "project":
            raise VerificationError("accountant dimension create failed")

        dimension = await _expect_status(
            client,
            "POST",
            "/api/v1/dimensions/",
            201,
            headers=admin_headers,
            json={"key": "cost_center", "name": "Cost Center"},
        )
        dimension_id = dimension.get("id")
        if not dimension_id:
            raise VerificationError("dimension id missing")

        value_one = await _expect_status(
            client,
            "POST",
            f"/api/v1/dimensions/{dimension_id}/values",
            201,
            headers=admin_headers,
            json={"code": "CC-001", "name": "Cost Center 1"},
        )
        value_two = await _expect_status(
            client,
            "POST",
            f"/api/v1/dimensions/{dimension_id}/values",
            201,
            headers=admin_headers,
            json={"code": "CC-002", "name": "Cost Center 2"},
        )
        value_one_id = value_one.get("id")
        value_two_id = value_two.get("id")
        if not value_one_id or not value_two_id:
            raise VerificationError("dimension value ids missing")

        await _expect_status(
            client,
            "POST",
            f"/api/v1/dimensions/values/{value_two_id}/archive",
            200,
            headers=admin_headers,
        )

        inactive_assign = await client.put(
            f"/api/v1/journal-lines/{line_ids[0]}/dimensions",
            headers=admin_headers,
            json={"dimensions": {"cost_center": value_two_id}},
        )
        if inactive_assign.status_code != 409:
            raise VerificationError("inactive dimension value assignment did not fail")
        if inactive_assign.json().get("code") != "dimension_value_inactive":
            raise VerificationError("inactive value error code missing")

        await _expect_status(
            client,
            "PUT",
            f"/api/v1/journal-lines/{line_ids[0]}/dimensions",
            200,
            headers=admin_headers,
            json={"dimensions": {"cost_center": value_one_id}},
        )
        await _expect_status(
            client,
            "PUT",
            f"/api/v1/journal-lines/{line_ids[1]}/dimensions",
            200,
            headers=admin_headers,
            json={"dimensions": {"cost_center": value_one_id}},
        )

        lookup = await _expect_status(
            client,
            "GET",
            f"/api/v1/journal-lines/{line_ids[0]}/dimensions",
            200,
            headers=admin_headers,
        )
        items = lookup.get("items") or []
        if not items:
            raise VerificationError("journal line dimensions missing")
        if items[0].get("dimension_key") != "cost_center":
            raise VerificationError("dimension key mismatch")
        if items[0].get("value_code") != "CC-001":
            raise VerificationError("dimension value mismatch")

        lookup_second = await _expect_status(
            client,
            "GET",
            f"/api/v1/journal-lines/{line_ids[1]}/dimensions",
            200,
            headers=admin_headers,
        )
        items_second = lookup_second.get("items") or []
        if not items_second:
            raise VerificationError("second journal line dimensions missing")

    async with session_maker() as session:
        service = LedgerService(session=session, tenant_id=tenant_id, actor_id=admin_user.id)
        await service.post_entry(entry.id)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        posted_assign = await client.put(
            f"/api/v1/journal-lines/{line_ids[0]}/dimensions",
            headers=admin_headers,
            json={"dimensions": {"cost_center": value_one_id}},
        )
        if posted_assign.status_code != 409:
            raise VerificationError("posted line dimension update did not fail")
        if posted_assign.json().get("code") != "journal_line_posted_immutable":
            raise VerificationError("posted line error code missing")

    print("Sprint 8 verification: OK")


def main() -> None:
    try:
        asyncio.run(run())
    except VerificationError as exc:
        print(f"Sprint 8 verification: FAILED - {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
