from __future__ import annotations

import asyncio
import os
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
        print("verify_sprint3: env file not loaded; relying on process environment")
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("BILLING_ENABLED", "false")
    os.environ.setdefault("JWT_SECRET_KEY", "dev-jwt-secret-key")
    os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "dev-jwt-refresh-secret-key")
    os.environ.setdefault("STRIPE_API_KEY", "sk_test_dummy")
    os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_dummy")


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


_prepare_environment()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.accounting.use_cases.lock_accounting_period import lock_accounting_period
from app.core.exceptions import AppException
from app.core.permissions import require_perm
from app.database import engine
from app.initial_data import seed_tenant
from app.models.account import Account
from app.models.audit_log import AuditLog
from app.models.role import Role
from app.models.tenant import Tenant
from app.schemas.journal_entry import JournalEntryUpdate
from app.schemas.journals import JournalLineCreate
from app.services import journal_service, user_service
from app.services.ledger_service import LedgerService


class VerificationError(RuntimeError):
    pass


async def _expect_app_exception(session, awaitable, *, code: str, label: str) -> None:
    try:
        await awaitable
    except AppException as exc:
        await session.rollback()
        if exc.code != code:
            raise VerificationError(
                f"{label} failed: expected {code}, got {exc.code} ({exc.message})"
            ) from exc
        return
    except Exception as exc:
        await session.rollback()
        raise VerificationError(
            f"{label} failed: expected {code}, got {type(exc).__name__}: {exc}"
        ) from exc
    raise VerificationError(f"{label} failed: expected {code}, got success")


async def _expect_permission_denied(dependency, *, user, label: str) -> None:
    try:
        await dependency(current_user=user)
    except AppException as exc:
        if exc.code != "permission_denied":
            raise VerificationError(
                f"{label} failed: expected permission_denied, got {exc.code} ({exc.message})"
            ) from exc
        return
    except Exception as exc:
        raise VerificationError(
            f"{label} failed: expected permission_denied, got {type(exc).__name__}: {exc}"
        ) from exc
    raise VerificationError(f"{label} failed: expected permission_denied, got success")


async def _assert_audit(session, tenant_id: uuid.UUID, action: str) -> None:
    result = await session.execute(
        select(AuditLog.id).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.action == action,
        )
    )
    if result.scalar_one_or_none() is None:
        raise VerificationError(f"audit check failed: missing action {action}")


async def _get_role(session, tenant_id: uuid.UUID, name: str) -> Role:
    result = await session.execute(
        select(Role).where(Role.tenant_id == tenant_id, Role.name == name)
    )
    role = result.scalar_one_or_none()
    if not role:
        raise VerificationError(f"role not found: {name}")
    return role


async def run() -> None:
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        tenant = Tenant(
            name="Sprint 3 Verify",
            slug=f"sprint3-verify-{uuid.uuid4().hex[:8]}",
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        tenant_id = tenant.id

        await seed_tenant(session, tenant)

        admin_role = await _get_role(session, tenant_id, "ADMIN")
        viewer_role = await _get_role(session, tenant_id, "VIEWER")
        admin_role_id = admin_role.id
        viewer_role_name = viewer_role.name

        admin_user = await user_service.create_user(
            session,
            tenant_id,
            {
                "email": f"admin-{tenant.slug}@example.com",
                "password": "Test1234",
                "full_name": "Sprint 3 Admin",
                "role_id": admin_role_id,
            },
        )
        viewer_user = await user_service.create_user(
            session,
            tenant_id,
            {
                "email": f"viewer-{tenant.slug}@example.com",
                "password": "Test1234",
                "full_name": "Sprint 3 Viewer",
                "role_id": viewer_role.id,
            },
        )
        admin_user_id = admin_user.id
        viewer_user_stub = {"role": viewer_role_name}

        accounts_result = await session.execute(
            select(Account).where(Account.tenant_id == tenant_id).order_by(Account.code.asc())
        )
        accounts = accounts_result.scalars().all()
        if len(accounts) < 2:
            raise VerificationError("expected at least two accounts for journal lines")

        debit_account_id = accounts[0].id
        credit_account_id = accounts[1].id
        entry_date = date.today()

        service = LedgerService(session=session, tenant_id=tenant_id, actor_id=admin_user_id)
        entry = await service.create_manual_entry(
            entry_date=entry_date,
            base_currency="USD",
            memo="Sprint 3 verify entry",
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

        posted_entry = await service.post_entry(entry.id)
        posted_entry_id = posted_entry.id

        await _expect_app_exception(
            session,
            journal_service.update_journal_entry(
                session,
                tenant_id,
                posted_entry_id,
                JournalEntryUpdate(description="blocked"),
            ),
            code="journal_posted_immutable",
            label="edit posted entry",
        )

        await _expect_app_exception(
            session,
            journal_service.delete_journal_entry(session, tenant_id, posted_entry_id),
            code="journal_posted_immutable",
            label="delete posted entry",
        )

        reversal = await service.reverse_entry(posted_entry_id, reason="Sprint 3 verification")
        if reversal.reversal_of_entry_id != posted_entry_id:
            raise VerificationError("reversal entry does not reference original entry")

        await _expect_app_exception(
            session,
            service.reverse_entry(posted_entry_id, reason="Sprint 3 verification again"),
            code="journal_already_reversed",
            label="second reversal",
        )

        await lock_accounting_period(
            session,
            tenant_id=tenant_id,
            start_date=entry_date,
            end_date=entry_date,
            actor_id=admin_user_id,
            commit=True,
        )

        locked_entry = await service.create_manual_entry(
            entry_date=entry_date,
            base_currency="USD",
            memo="Sprint 3 locked period entry",
            source_type="manual",
            source_id=None,
            lines=[
                JournalLineCreate(
                    account_id=debit_account_id,
                    debit_amount=Decimal("50.00"),
                    credit_amount=Decimal("0.00"),
                    line_currency="USD",
                ),
                JournalLineCreate(
                    account_id=credit_account_id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=Decimal("50.00"),
                    line_currency="USD",
                ),
            ],
        )
        locked_entry_id = locked_entry.id

        await _expect_app_exception(
            session,
            service.post_entry(locked_entry_id),
            code="accounting_period_locked",
            label="post into locked period",
        )

        await _assert_audit(session, tenant_id, "journal.post")
        await _assert_audit(session, tenant_id, "journal.reverse")
        await _assert_audit(session, tenant_id, "period.lock")

        await _expect_permission_denied(
            require_perm("journal.post"),
            user=viewer_user_stub,
            label="unauthorized post permission",
        )
        await _expect_permission_denied(
            require_perm("journal.reverse"),
            user=viewer_user_stub,
            label="unauthorized reversal permission",
        )
        await _expect_permission_denied(
            require_perm("period.lock"),
            user=viewer_user_stub,
            label="unauthorized period lock permission",
        )

    print("Sprint 3 verification: OK")


def main() -> None:
    try:
        asyncio.run(run())
    except VerificationError as exc:
        print(f"Sprint 3 verification: FAILED - {exc}")
        sys.exit(1)
    except AppException as exc:
        print(f"Sprint 3 verification: FAILED - {exc.code}: {exc.message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
