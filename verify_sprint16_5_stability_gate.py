from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import uuid
from datetime import UTC, date, datetime
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
        print("verify_sprint16_5: env file not loaded; relying on process environment")
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
from app.models.journal_entry import JournalEntry  # noqa: E402
from app.models.journal_line import JournalLine  # noqa: E402
from app.models.role import Role  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.models.treasury_cash_transaction import (  # noqa: E402
    CashTransactionStatus,
    TreasuryCashTransaction,
)
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
            name=f"Sprint 16.5 {label}",
            slug=f"sprint16-5-{label}-{uuid.uuid4().hex[:8]}",
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
                "full_name": f"Sprint 16.5 {label} Admin",
                "role_id": admin_role.id,
            },
        )
        token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )
        return tenant_id, token


async def _get_account_by_code(session: AsyncSession, tenant_id: uuid.UUID, code: str) -> Account:
    result = await session.execute(
        select(Account).where(Account.tenant_id == tenant_id, Account.code == code)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise VerificationError(f"account {code} not found for tenant {tenant_id}")
    return account


def _ai_run_meta(*, scenario: str) -> dict:
    return {
        "model_name": "stability-gate-model",
        "model_version": "2026.01",
        "dataset_fingerprint": "fp-16-5",
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": "verify_sprint16_5",
        "date_from": "2025-10-01",
        "date_to": "2025-12-31",
        "scenario": scenario,
    }


def _ai_payload(label: str) -> dict:
    return {
        "forecast": {
            "series": [
                {
                    "name": f"cash_balance_{label}",
                    "freq": "monthly",
                    "currency": "USD",
                    "points": [
                        {"t": "2026-02", "y": 100.0, "lo": 95.0, "hi": 110.0},
                        {"t": "2026-03", "y": 105.0, "lo": 98.0, "hi": 112.0},
                    ],
                }
            ],
            "backtest": {"metric": "MAPE", "value": 0.11, "window": "6m"},
            "confidence_note": "Stable demand trend.",
        },
        "risk": {
            "items": [
                {
                    "id": f"risk-{label}",
                    "title": "Receivables concentration",
                    "severity": "medium",
                    "confidence": 0.62,
                    "evidence": ["Top 2 customers are 45% of revenue."],
                    "suggested_actions": ["Diversify customer base"],
                }
            ]
        },
        "explainability": {
            "drivers": [
                {
                    "factor": "sales_volume",
                    "direction": "up",
                    "weight": 0.62,
                    "narrative": "Higher sales volumes drove the forecast uplift.",
                }
            ],
            "overall_confidence": 0.7,
        },
        "insights": {
            "bullets": [
                {
                    "title": "Cash balance trending up",
                    "detail": "Projected cash balance rises over next quarter.",
                    "confidence": 0.66,
                    "tags": ["forecast"],
                }
            ]
        },
    }


async def _snapshot_financials(
    session_maker: async_sessionmaker[AsyncSession],
    tenant_id: uuid.UUID,
) -> dict[str, Decimal]:
    async with session_maker() as session:
        entry_count = await session.scalar(
            select(func.count()).select_from(JournalEntry).where(JournalEntry.tenant_id == tenant_id)
        )
        line_count = await session.scalar(
            select(func.count()).select_from(JournalLine).where(JournalLine.tenant_id == tenant_id)
        )
        posted_tx_count = await session.scalar(
            select(func.count())
            .select_from(TreasuryCashTransaction)
            .where(
                TreasuryCashTransaction.tenant_id == tenant_id,
                TreasuryCashTransaction.status == CashTransactionStatus.POSTED,
            )
        )
    return {
        "journal_entries": Decimal(entry_count or 0),
        "journal_lines": Decimal(line_count or 0),
        "posted_cash_transactions": Decimal(posted_tx_count or 0),
    }


async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    tenant_a_id, token_a = await _create_tenant_with_admin(session_maker, "tenant-a")
    tenant_b_id, token_b = await _create_tenant_with_admin(session_maker, "tenant-b")
    headers_a = _auth_headers(token_a, tenant_a_id)
    headers_b = _auth_headers(token_b, tenant_b_id)

    async with session_maker() as session:
        cash_account = await _get_account_by_code(session, tenant_a_id, "1100")
        revenue_account = await _get_account_by_code(session, tenant_a_id, "4000")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("TEST 1: tenant isolation")
        cash_account_payload = {
            "name": "Sprint 16.5 Cash",
            "account_id": str(cash_account.id),
            "description": "Sprint 16.5 cash account",
        }
        cash_account_resp = await _expect_status(
            client,
            "POST",
            "/api/v1/treasury/cash-accounts",
            201,
            headers=headers_a,
            json=cash_account_payload,
        )
        cash_account_id = cash_account_resp["id"]

        posting_date = date.today().isoformat()
        tx_payload = {
            "transaction_type": "RECEIPT",
            "amount": "100.00",
            "posting_date": posting_date,
            "cash_account_id": cash_account_id,
            "counterparty_account_id": str(revenue_account.id),
            "description": "Sprint 16.5 receipt",
        }
        tx = await _expect_status(
            client,
            "POST",
            "/api/v1/treasury/transactions",
            201,
            headers=headers_a,
            json=tx_payload,
        )
        tx_id = tx["id"]

        posted = await _expect_status(
            client,
            "POST",
            f"/api/v1/treasury/transactions/{tx_id}/post",
            200,
            headers=headers_a,
        )
        posted_entry_id = posted.get("journal_entry_id")
        if not posted_entry_id:
            raise VerificationError("posted cash transaction missing journal_entry_id")

        await _expect_error(
            client,
            "GET",
            f"/api/v1/journals/{posted_entry_id}",
            404,
            "http_error",
            headers=headers_b,
        )

        print("TEST 2: posting idempotency")
        await _expect_error(
            client,
            "POST",
            f"/api/v1/treasury/transactions/{tx_id}/post",
            409,
            "cash_transaction_already_posted",
            headers=headers_a,
        )

        async with session_maker() as session:
            source_count = await session.scalar(
                select(func.count())
                .select_from(JournalEntry)
                .where(
                    JournalEntry.tenant_id == tenant_a_id,
                    JournalEntry.source_type == "treasury_cash",
                    JournalEntry.source_id == uuid.UUID(tx_id),
                )
            )
        if int(source_count or 0) != 1:
            raise VerificationError("cash transaction posted more than one journal entry")

        print("TEST 3: reversal correctness + idempotency")
        reversed_tx = await _expect_status(
            client,
            "POST",
            f"/api/v1/treasury/transactions/{tx_id}/reverse",
            200,
            headers=headers_a,
            json={"reason": "stability gate reversal"},
        )
        reversal_entry_id = reversed_tx.get("reversal_journal_entry_id")
        if not reversal_entry_id:
            raise VerificationError("reversal cash transaction missing reversal journal entry")

        async with session_maker() as session:
            sums = await session.execute(
                select(
                    func.coalesce(func.sum(JournalLine.debit_base), 0),
                    func.coalesce(func.sum(JournalLine.credit_base), 0),
                ).where(
                    JournalLine.tenant_id == tenant_a_id,
                    JournalLine.entry_id == uuid.UUID(reversal_entry_id),
                )
            )
            debit_total, credit_total = sums.one()
            debit_total = Decimal(str(debit_total))
            credit_total = Decimal(str(credit_total))
            if debit_total != credit_total or debit_total <= 0:
                raise VerificationError("reversal journal entry is not balanced")

            reversal_count = await session.scalar(
                select(func.count())
                .select_from(JournalEntry)
                .where(
                    JournalEntry.tenant_id == tenant_a_id,
                    JournalEntry.reversed_of_id == uuid.UUID(posted_entry_id),
                )
            )
        if int(reversal_count or 0) != 1:
            raise VerificationError("expected exactly one reversal journal entry")

        await _expect_error(
            client,
            "POST",
            f"/api/v1/treasury/transactions/{tx_id}/reverse",
            409,
            "cash_transaction_already_reversed",
            headers=headers_a,
            json={"reason": "second reversal attempt"},
        )

        print("TEST 4: period lock enforcement")
        tx2 = await _expect_status(
            client,
            "POST",
            "/api/v1/treasury/transactions",
            201,
            headers=headers_a,
            json={
                **tx_payload,
                "description": "Sprint 16.5 lock target",
            },
        )
        tx2_id = tx2["id"]
        await _expect_status(
            client,
            "POST",
            f"/api/v1/treasury/transactions/{tx2_id}/post",
            200,
            headers=headers_a,
        )

        lock = await _expect_status(
            client,
            "POST",
            "/api/v1/journals/period-locks",
            201,
            headers=headers_a,
            json={"start_date": posting_date, "end_date": posting_date},
        )
        lock_id = lock.get("id")

        tx3 = await _expect_status(
            client,
            "POST",
            "/api/v1/treasury/transactions",
            201,
            headers=headers_a,
            json={**tx_payload, "description": "Sprint 16.5 locked post"},
        )
        tx3_id = tx3["id"]
        await _expect_error(
            client,
            "POST",
            f"/api/v1/treasury/transactions/{tx3_id}/post",
            409,
            "accounting_period_locked",
            headers=headers_a,
        )

        await _expect_error(
            client,
            "POST",
            f"/api/v1/treasury/transactions/{tx2_id}/reverse",
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

        print("TEST 5: AI ingest immutability & no ledger mutation")
        snapshot_before = await _snapshot_financials(session_maker, tenant_a_id)
        ai_request = {
            "schema_version": "1.0",
            "run_meta": _ai_run_meta(scenario="baseline"),
            "payload": _ai_payload("a"),
            "signature": None,
        }
        ai_run = await _expect_status(
            client,
            "POST",
            "/api/v1/ai/runs",
            201,
            headers=headers_a,
            json=ai_request,
        )

        snapshot_after = await _snapshot_financials(session_maker, tenant_a_id)
        if snapshot_before != snapshot_after:
            raise VerificationError("AI ingest mutated financial records")

        await _expect_error(
            client,
            "GET",
            f"/api/v1/ai/runs/{ai_run['id']}",
            404,
            "ai_run_not_found",
            headers=headers_b,
        )

        await _expect_error(
            client,
            "POST",
            "/api/v1/ai/runs",
            409,
            "ai_run_already_exists",
            headers=headers_a,
            json=ai_request,
        )

    print("SPRINT 16.5 VERIFIED OK")


if __name__ == "__main__":
    asyncio.run(run())
