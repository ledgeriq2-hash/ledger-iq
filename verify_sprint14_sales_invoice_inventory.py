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
        print("verify_sprint14_sales_invoice_inventory: env file not loaded; relying on process environment")
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
from app.models.account import Account
from app.models.account_mapping import AccountMapping
from app.models.journal_entry import JournalEntry
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
    result = await session.execute(select(Role).where(Role.tenant_id == tenant_id, Role.name == name))
    role = result.scalar_one_or_none()
    if not role:
        raise VerificationError(f"role not found: {name}")
    return role


def _auth_headers(token: str, tenant_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Tenant-Id": str(tenant_id)}


def _quantize(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


async def _get_or_create_account(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    code: str,
    name: str,
    account_type: str,
    normal_balance: str,
) -> Account:
    result = await session.execute(select(Account).where(Account.tenant_id == tenant_id, Account.code == code))
    account = result.scalar_one_or_none()
    if account:
        return account
    account = Account(
        tenant_id=tenant_id,
        code=code,
        name=name,
        type=account_type,
        normal_balance=normal_balance,
        is_system=False,
        is_active=True,
    )
    session.add(account)
    await session.flush()
    return account


async def _get_ar_control_account_id(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    result = await session.execute(
        select(AccountMapping).where(
            AccountMapping.tenant_id == tenant_id,
            AccountMapping.key == "AR_CONTROL",
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise VerificationError("AR_CONTROL account mapping missing")
    return mapping.account_id


async def _fetch_invoice_entries(
    session: AsyncSession, tenant_id: uuid.UUID, invoice_id: uuid.UUID
) -> list[JournalEntry]:
    result = await session.execute(
        select(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.source_type == "sales_invoice",
            JournalEntry.source_id == invoice_id,
        )
        .order_by(JournalEntry.created_at.desc())
    )
    return list(result.scalars().all())


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
        raise VerificationError(f"{method} {path} returned {response.status_code}: {response.text}")
    return response.json() if response.text else {}


async def _list_stock_moves(
    client: AsyncClient,
    *,
    headers: dict[str, str],
    reference_type: str,
    reference_id: str,
) -> list[dict]:
    payload = await _expect_status(
        client,
        "GET",
        "/api/v1/stock/moves",
        200,
        headers=headers,
        params={"reference_type": reference_type, "reference_id": reference_id},
    )
    return payload.get("items") or []


async def run() -> None:
    _run_migrations()

    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        tenant = Tenant(
            name="Sprint 14 Sales Inventory",
            slug=f"sprint14-sales-inv-{uuid.uuid4().hex[:8]}",
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
                "full_name": "Sprint 14 Admin",
                "role_id": admin_role.id,
            },
        )
        admin_token = create_access_token(
            str(admin_user.id),
            claims={"tenant_id": str(tenant_id), "token_version": 0},
        )

        _ = await _get_ar_control_account_id(session, tenant_id)
        revenue_account = await session.scalar(
            select(Account)
            .where(Account.tenant_id == tenant_id, Account.type.in_(["INCOME", "REVENUE"]))
            .order_by(Account.code.asc())
        )
        if not revenue_account:
            revenue_account = await _get_or_create_account(
                session,
                tenant_id,
                code="4000",
                name="Revenue",
                account_type="INCOME",
                normal_balance="credit",
            )
        revenue_account_id = revenue_account.id

    admin_headers = _auth_headers(admin_token, tenant_id)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unit = await _expect_status(
            client,
            "POST",
            "/api/v1/units/",
            201,
            headers=admin_headers,
            json={"code": f"EA14-{uuid.uuid4().hex[:4]}", "name": "Each", "is_base": True},
        )
        unit_id = unit.get("id")
        if not unit_id:
            raise VerificationError("unit id missing")

        product = await _expect_status(
            client,
            "POST",
            "/api/v1/products/",
            201,
            headers=admin_headers,
            json={
                "sku": f"P14-SI-{uuid.uuid4().hex[:6]}",
                "name": "Sales Item",
                "status": "ACTIVE",
                "base_unit_id": unit_id,
            },
        )
        product_id = product.get("id")
        if not product_id:
            raise VerificationError("product id missing")

        customer = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=admin_headers,
            json={"code": f"CUST-14-{uuid.uuid4().hex[:6]}", "name": "Sprint 14 Customer"},
        )
        customer_id = customer.get("id")
        if not customer_id:
            raise VerificationError("customer id missing")

        invoice_date = date.today()
        seed_move = await _expect_status(
            client,
            "POST",
            "/api/v1/stock/moves",
            201,
            headers=admin_headers,
            json={
                "product_id": product_id,
                "move_date": invoice_date.isoformat(),
                "direction": "IN",
                "quantity_base": "5",
                "reference_type": "manual_adjustment",
                "reference_id": str(uuid.uuid4()),
            },
        )
        if _quantize(seed_move.get("quantity_base", 0)) != Decimal("5.00"):
            raise VerificationError("seed IN move quantity mismatch")

        balance = await _expect_status(
            client,
            "GET",
            f"/api/v1/stock/balances/{product_id}",
            200,
            headers=admin_headers,
        )
        if _quantize(balance.get("on_hand_qty_base", 0)) != Decimal("5.00"):
            raise VerificationError("seed stock balance not updated")

        invoice_no = f"SI-INV-{uuid.uuid4().hex[:6]}"
        line_one = {
            "line_no": 1,
            "description": "Item A",
            "quantity": "2",
            "unit_id": unit_id,
            "unit_price": "30.00",
            "amount": "60.00",
            "product_id": product_id,
            "revenue_account_id": str(revenue_account_id),
        }
        line_two = {
            "line_no": 2,
            "description": "Item B",
            "quantity": "1",
            "unit_id": unit_id,
            "unit_price": "20.00",
            "amount": "20.00",
            "product_id": product_id,
            "revenue_account_id": str(revenue_account_id),
        }
        sale_qty = _quantize("3.00")

        draft = await _expect_status(
            client,
            "POST",
            "/api/v1/sales-invoices/",
            201,
            headers=admin_headers,
            json={
                "customer_id": customer_id,
                "invoice_no": invoice_no,
                "invoice_date": invoice_date.isoformat(),
                "currency_code": "USD",
                "lines": [line_one, line_two],
            },
        )
        invoice_id = draft.get("id")
        if not invoice_id:
            raise VerificationError("sales invoice id missing")
        if draft.get("status") != "DRAFT":
            raise VerificationError("sales invoice draft status incorrect")

        draft_moves = await _list_stock_moves(
            client, headers=admin_headers, reference_type="sales_invoice", reference_id=invoice_id
        )
        if draft_moves:
            raise VerificationError("draft sales invoice created stock moves")

        posted = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/post",
            200,
            headers=admin_headers,
        )
        if posted.get("status") != "POSTED":
            raise VerificationError("sales invoice did not post")

        posted_moves = await _list_stock_moves(
            client, headers=admin_headers, reference_type="sales_invoice", reference_id=invoice_id
        )
        if not posted_moves:
            raise VerificationError("sales invoice did not create stock moves")
        if any(move.get("direction") != "OUT" for move in posted_moves):
            raise VerificationError("sales invoice stock move direction mismatch")
        qty_total = sum((_quantize(move.get("quantity_base", 0)) for move in posted_moves), Decimal("0.00"))
        if qty_total != sale_qty:
            raise VerificationError("sales invoice stock quantity total mismatch")

        balance_after_post = await _expect_status(
            client,
            "GET",
            f"/api/v1/stock/balances/{product_id}",
            200,
            headers=admin_headers,
        )
        if _quantize(balance_after_post.get("on_hand_qty_base", 0)) != Decimal("2.00"):
            raise VerificationError("sales invoice did not update stock balance")

        posted_again = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/post",
            200,
            headers=admin_headers,
        )
        if posted_again.get("status") != "POSTED":
            raise VerificationError("posting again changed sales invoice status")

        moves_after_post_again = await _list_stock_moves(
            client, headers=admin_headers, reference_type="sales_invoice", reference_id=invoice_id
        )
        if len(moves_after_post_again) != len(posted_moves):
            raise VerificationError("posting sales invoice twice created extra stock moves")

        negative_invoice = await _expect_status(
            client,
            "POST",
            "/api/v1/sales-invoices/",
            201,
            headers=admin_headers,
            json={
                "customer_id": customer_id,
                "invoice_no": f"SI-NEG-{uuid.uuid4().hex[:6]}",
                "invoice_date": invoice_date.isoformat(),
                "currency_code": "USD",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Over-sell",
                        "quantity": "5",
                        "unit_id": unit_id,
                        "unit_price": "10.00",
                        "amount": "50.00",
                        "product_id": product_id,
                        "revenue_account_id": str(revenue_account_id),
                    }
                ],
            },
        )
        negative_invoice_id = negative_invoice.get("id")
        if not negative_invoice_id:
            raise VerificationError("negative stock invoice id missing")

        negative_resp = await client.post(
            f"/api/v1/sales-invoices/{negative_invoice_id}/post",
            headers=admin_headers,
        )
        if negative_resp.status_code != 409:
            raise VerificationError("posting sales invoice with insufficient stock did not fail")
        if negative_resp.json().get("code") != "insufficient_stock":
            raise VerificationError("insufficient stock error code mismatch")

        negative_moves = await _list_stock_moves(
            client, headers=admin_headers, reference_type="sales_invoice", reference_id=negative_invoice_id
        )
        if negative_moves:
            raise VerificationError("failed sales post created stock moves")

        async with session_maker() as session:
            entries = await _fetch_invoice_entries(session, tenant_id, uuid.UUID(negative_invoice_id))
            if entries:
                raise VerificationError("failed sales post created journal entry")

        balance_after_fail = await _expect_status(
            client,
            "GET",
            f"/api/v1/stock/balances/{product_id}",
            200,
            headers=admin_headers,
        )
        if _quantize(balance_after_fail.get("on_hand_qty_base", 0)) != Decimal("2.00"):
            raise VerificationError("balance changed after failed sales post")

        reversed_invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/reverse",
            200,
            headers=admin_headers,
            json={"reason": "Sprint 14 reversal"},
        )
        if reversed_invoice.get("status") != "REVERSED":
            raise VerificationError("sales invoice did not reverse")

        reversal_moves = await _list_stock_moves(
            client,
            headers=admin_headers,
            reference_type="sales_invoice_reverse",
            reference_id=invoice_id,
        )
        if not reversal_moves:
            raise VerificationError("sales invoice reversal stock moves missing")
        if any(move.get("direction") != "IN" for move in reversal_moves):
            raise VerificationError("sales invoice reversal move direction mismatch")
        reversal_qty = sum((_quantize(move.get("quantity_base", 0)) for move in reversal_moves), Decimal("0.00"))
        if reversal_qty != sale_qty:
            raise VerificationError("sales invoice reversal quantity mismatch")

        balance_after_reverse = await _expect_status(
            client,
            "GET",
            f"/api/v1/stock/balances/{product_id}",
            200,
            headers=admin_headers,
        )
        if _quantize(balance_after_reverse.get("on_hand_qty_base", 0)) != Decimal("5.00"):
            raise VerificationError("sales invoice reversal did not restore stock balance")

        reversed_again = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{invoice_id}/reverse",
            200,
            headers=admin_headers,
            json={"reason": "Sprint 14 reversal again"},
        )
        if reversed_again.get("status") != "REVERSED":
            raise VerificationError("second reversal changed sales invoice status unexpectedly")

        reversal_moves_again = await _list_stock_moves(
            client,
            headers=admin_headers,
            reference_type="sales_invoice_reverse",
            reference_id=invoice_id,
        )
        if len(reversal_moves_again) != len(reversal_moves):
            raise VerificationError("second reversal created extra stock moves")

        lock_date = invoice_date
        lock_customer = await _expect_status(
            client,
            "POST",
            "/api/v1/customers/",
            201,
            headers=admin_headers,
            json={"code": f"CUST-14-LOCK-{uuid.uuid4().hex[:4]}", "name": "Locked Customer"},
        )
        locked_customer_id = lock_customer.get("id")
        if not locked_customer_id:
            raise VerificationError("locked customer id missing")

        lock_candidate = await _expect_status(
            client,
            "POST",
            "/api/v1/sales-invoices/",
            201,
            headers=admin_headers,
            json={
                "customer_id": locked_customer_id,
                "invoice_no": f"SI-LOCK-{uuid.uuid4().hex[:6]}",
                "invoice_date": lock_date.isoformat(),
                "currency_code": "USD",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Lock candidate",
                        "quantity": "1",
                        "unit_id": unit_id,
                        "unit_price": "5.00",
                        "amount": "5.00",
                        "product_id": product_id,
                        "revenue_account_id": str(revenue_account_id),
                    }
                ],
            },
        )
        lock_candidate_id = lock_candidate.get("id")
        if not lock_candidate_id:
            raise VerificationError("lock candidate invoice id missing")

        posted_candidate = await _expect_status(
            client,
            "POST",
            f"/api/v1/sales-invoices/{lock_candidate_id}/post",
            200,
            headers=admin_headers,
        )
        if posted_candidate.get("status") != "POSTED":
            raise VerificationError("pre-lock sales invoice did not post")

        await _expect_status(
            client,
            "POST",
            "/api/v1/journals/period-locks",
            201,
            headers=admin_headers,
            json={"start_date": lock_date.isoformat(), "end_date": lock_date.isoformat()},
        )

        reverse_locked = await client.post(
            f"/api/v1/sales-invoices/{lock_candidate_id}/reverse",
            headers=admin_headers,
            json={"reason": "Locked reverse"},
        )
        if reverse_locked.status_code != 409:
            raise VerificationError("reversal in locked period did not fail")
        if reverse_locked.json().get("code") != "accounting_period_locked":
            raise VerificationError("locked period error code mismatch on reverse")

        locked_draft = await _expect_status(
            client,
            "POST",
            "/api/v1/sales-invoices/",
            201,
            headers=admin_headers,
            json={
                "customer_id": locked_customer_id,
                "invoice_no": f"SI-LOCK2-{uuid.uuid4().hex[:6]}",
                "invoice_date": lock_date.isoformat(),
                "currency_code": "USD",
                "lines": [
                    {
                        "line_no": 1,
                        "description": "Locked draft",
                        "quantity": "1",
                        "unit_id": unit_id,
                        "unit_price": "3.00",
                        "amount": "3.00",
                        "product_id": product_id,
                        "revenue_account_id": str(revenue_account_id),
                    }
                ],
            },
        )
        locked_draft_id = locked_draft.get("id")
        if not locked_draft_id:
            raise VerificationError("locked draft invoice id missing")

        post_locked = await client.post(
            f"/api/v1/sales-invoices/{locked_draft_id}/post",
            headers=admin_headers,
        )
        if post_locked.status_code != 409:
            raise VerificationError("posting draft in locked period did not fail")
        if post_locked.json().get("code") != "accounting_period_locked":
            raise VerificationError("locked period error code mismatch on post")

    print("Sprint 14 sales invoice inventory verification: OK")


def main() -> None:
    try:
        asyncio.run(run())
    except VerificationError as exc:
        print(f"Sprint 14 sales invoice inventory verification: FAILED - {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
