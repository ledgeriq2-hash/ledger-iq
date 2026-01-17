from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.accounting.use_cases.lock_accounting_period import lock_accounting_period
from app.core.exceptions import AppException
from app.core.permissions import require_perm
from app.database import async_session_maker
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
    async with async_session_maker() as session:
        tenant = Tenant(
            name="Sprint 3 Verify",
            slug=f"sprint3-verify-{uuid.uuid4().hex[:8]}",
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        await seed_tenant(session, tenant)

        admin_role = await _get_role(session, tenant.id, "ADMIN")
        viewer_role = await _get_role(session, tenant.id, "VIEWER")

        admin_user = await user_service.create_user(
            session,
            tenant.id,
            {
                "email": f"admin-{tenant.slug}@example.com",
                "password": "Test1234",
                "full_name": "Sprint 3 Admin",
                "role_id": admin_role.id,
            },
        )
        viewer_user = await user_service.create_user(
            session,
            tenant.id,
            {
                "email": f"viewer-{tenant.slug}@example.com",
                "password": "Test1234",
                "full_name": "Sprint 3 Viewer",
                "role_id": viewer_role.id,
            },
        )
        admin_user.role = admin_role
        viewer_user.role = viewer_role

        accounts_result = await session.execute(
            select(Account).where(Account.tenant_id == tenant.id).order_by(Account.code.asc())
        )
        accounts = accounts_result.scalars().all()
        if len(accounts) < 2:
            raise VerificationError("expected at least two accounts for journal lines")

        debit_account = accounts[0]
        credit_account = accounts[1]
        entry_date = date.today()

        service = LedgerService(session=session, tenant_id=tenant.id, actor_id=admin_user.id)
        entry = await service.create_manual_entry(
            entry_date=entry_date,
            base_currency="USD",
            memo="Sprint 3 verify entry",
            source_type="manual",
            source_id=None,
            lines=[
                JournalLineCreate(
                    account_id=debit_account.id,
                    debit_amount=Decimal("100.00"),
                    credit_amount=Decimal("0.00"),
                    line_currency="USD",
                ),
                JournalLineCreate(
                    account_id=credit_account.id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=Decimal("100.00"),
                    line_currency="USD",
                ),
            ],
        )

        posted_entry = await service.post_entry(entry.id)

        await _expect_app_exception(
            session,
            journal_service.update_journal_entry(
                session,
                tenant.id,
                posted_entry.id,
                JournalEntryUpdate(description="blocked"),
            ),
            code="journal_posted_immutable",
            label="edit posted entry",
        )

        await _expect_app_exception(
            session,
            journal_service.delete_journal_entry(session, tenant.id, posted_entry.id),
            code="journal_posted_immutable",
            label="delete posted entry",
        )

        reversal = await service.reverse_entry(posted_entry.id, reason="Sprint 3 verification")
        if reversal.reversal_of_entry_id != posted_entry.id:
            raise VerificationError("reversal entry does not reference original entry")

        await _expect_app_exception(
            session,
            service.reverse_entry(posted_entry.id, reason="Sprint 3 verification again"),
            code="journal_already_reversed",
            label="second reversal",
        )

        await lock_accounting_period(
            session,
            tenant_id=tenant.id,
            start_date=entry_date,
            end_date=entry_date,
            actor_id=admin_user.id,
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
                    account_id=debit_account.id,
                    debit_amount=Decimal("50.00"),
                    credit_amount=Decimal("0.00"),
                    line_currency="USD",
                ),
                JournalLineCreate(
                    account_id=credit_account.id,
                    debit_amount=Decimal("0.00"),
                    credit_amount=Decimal("50.00"),
                    line_currency="USD",
                ),
            ],
        )

        await _expect_app_exception(
            session,
            service.post_entry(locked_entry.id),
            code="accounting_period_locked",
            label="post into locked period",
        )

        await _assert_audit(session, tenant.id, "journal.post")
        await _assert_audit(session, tenant.id, "journal.reverse")
        await _assert_audit(session, tenant.id, "period.lock")

        await _expect_permission_denied(
            require_perm("journal.post"),
            user=viewer_user,
            label="unauthorized post permission",
        )
        await _expect_permission_denied(
            require_perm("journal.reverse"),
            user=viewer_user,
            label="unauthorized reversal permission",
        )
        await _expect_permission_denied(
            require_perm("period.lock"),
            user=viewer_user,
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
