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
        print("verify_sprint14_purchase_invoice_inventory: env file not loaded; relying on process environment")
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


async def _get_ap_control_account_id(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    result = await session.execute(
        select(AccountMapping).where(
            AccountMapping.tenant_id == tenant_id,
            AccountMapping.key == "AP_CONTROL",
        )
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise VerificationError("AP_CONTROL account mapping missing")
    return mapping.account_id


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
            name="Sprint 14 Purchase Inventory",
            slug=f"sprint14-purch-inv-{uuid.uuid4().hex[:8]}",
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

        _ = await _get_ap_control_account_id(session, tenant_id)
        expense_account = await session.scalar(
            select(Account)
            .where(Account.tenant_id == tenant_id, Account.type.in_(["EXPENSE", "COGS"]))
            .order_by(Account.code.asc())
        )
        if not expense_account:
            expense_account = await _get_or_create_account(
                session,
                tenant_id,
                code="5000",
                name="Expenses",
                account_type="EXPENSE",
                normal_balance="debit",
            )
        expense_account_id = expense_account.id

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
                "sku": f"P14-PI-{uuid.uuid4().hex[:6]}",
                "name": "Purchase Item",
                "status": "ACTIVE",
                "base_unit_id": unit_id,
            },
        )
        product_id = product.get("id")
        if not product_id:
            raise VerificationError("product id missing")

        vendor = await _expect_status(
            client,
            "POST",
            "/api/v1/vendors/",
            201,
            headers=admin_headers,
            json={"code": f"VEND-14-{uuid.uuid4().hex[:6]}", "name": "Sprint 14 Vendor"},
        )
        vendor_id = vendor.get("id")
        if not vendor_id:
            raise VerificationError("vendor id missing")

        balance = await _expect_status(
            client,
            "GET",
            f"/api/v1/stock/balances/{product_id}",
            200,
            headers=admin_headers,
        )
        initial_balance = _quantize(balance.get("on_hand_qty_base", 0))
        if initial_balance != Decimal("0.00"):
            raise VerificationError("initial stock balance is not zero")

        invoice_date = date.today()
        invoice_no = f"PI-INV-{uuid.uuid4().hex[:6]}"
        line_one = {
            "line_no": 1,
            "description": "Materials",
            "quantity": "2",
            "unit_id": unit_id,
            "unit_price": "10.00",
            "amount": "20.00",
            "product_id": product_id,
            "expense_account_id": str(expense_account_id),
        }
        line_two = {
            "line_no": 2,
            "description": "Services",
            "quantity": "3",
            "unit_id": unit_id,
            "unit_price": "15.00",
            "amount": "45.00",
            "product_id": product_id,
            "expense_account_id": str(expense_account_id),
        }
        total_qty = _quantize("5.00")

        draft = await _expect_status(
            client,
            "POST",
            "/api/v1/purchase-invoices/",
            201,
            headers=admin_headers,
            json={
                "vendor_id": vendor_id,
                "invoice_no": invoice_no,
                "invoice_date": invoice_date.isoformat(),
                "currency_code": "USD",
                "lines": [line_one, line_two],
            },
        )
        invoice_id = draft.get("id")
        if not invoice_id:
            raise VerificationError("purchase invoice id missing")
        if draft.get("status") != "DRAFT":
            raise VerificationError("purchase invoice draft status incorrect")

        balance_after_draft = await _expect_status(
            client,
            "GET",
            f"/api/v1/stock/balances/{product_id}",
            200,
            headers=admin_headers,
        )
        if _quantize(balance_after_draft.get("on_hand_qty_base", 0)) != initial_balance:
            raise VerificationError("draft purchase invoice changed stock balance")

        draft_moves = await _list_stock_moves(
            client, headers=admin_headers, reference_type="purchase_invoice", reference_id=invoice_id
        )
        if draft_moves:
            raise VerificationError("draft purchase invoice created stock moves")

        posted = await _expect_status(
            client,
            "POST",
            f"/api/v1/purchase-invoices/{invoice_id}/post",
            200,
            headers=admin_headers,
        )
        if posted.get("status") != "POSTED":
            raise VerificationError("purchase invoice did not post")

        posted_moves = await _list_stock_moves(
            client, headers=admin_headers, reference_type="purchase_invoice", reference_id=invoice_id
        )
        if not posted_moves:
            raise VerificationError("purchase invoice did not create stock moves")
        if any(move.get("direction") != "IN" for move in posted_moves):
            raise VerificationError("purchase invoice stock move direction mismatch")
        qty_total = sum((_quantize(move.get("quantity_base", 0)) for move in posted_moves), Decimal("0.00"))
        if qty_total != total_qty:
            raise VerificationError("purchase invoice stock quantity total mismatch")

        balance_after_post = await _expect_status(
            client,
            "GET",
            f"/api/v1/stock/balances/{product_id}",
            200,
            headers=admin_headers,
        )
        if _quantize(balance_after_post.get("on_hand_qty_base", 0)) != total_qty:
            raise VerificationError("purchase invoice did not update stock balance")

        posted_again = await _expect_status(
            client,
            "POST",
            f"/api/v1/purchase-invoices/{invoice_id}/post",
            200,
            headers=admin_headers,
        )
        if posted_again.get("status") != "POSTED":
            raise VerificationError("posting again changed purchase invoice status")

        moves_after_post_again = await _list_stock_moves(
            client, headers=admin_headers, reference_type="purchase_invoice", reference_id=invoice_id
        )
        if len(moves_after_post_again) != len(posted_moves):
            raise VerificationError("posting purchase invoice twice created extra stock moves")

        reversed_invoice = await _expect_status(
            client,
            "POST",
            f"/api/v1/purchase-invoices/{invoice_id}/reverse",
            200,
            headers=admin_headers,
            json={"reason": "Sprint 14 reversal"},
        )
        if reversed_invoice.get("status") != "REVERSED":
            raise VerificationError("purchase invoice did not reverse")

        reversal_moves = await _list_stock_moves(
            client,
            headers=admin_headers,
            reference_type="purchase_invoice_reverse",
            reference_id=invoice_id,
        )
        if not reversal_moves:
            raise VerificationError("purchase invoice reversal stock moves missing")
        if any(move.get("direction") != "OUT" for move in reversal_moves):
            raise VerificationError("purchase invoice reversal move direction mismatch")
        reversal_qty = sum((_quantize(move.get("quantity_base", 0)) for move in reversal_moves), Decimal("0.00"))
        if reversal_qty != total_qty:
            raise VerificationError("purchase invoice reversal quantity mismatch")

        balance_after_reverse = await _expect_status(
            client,
            "GET",
            f"/api/v1/stock/balances/{product_id}",
            200,
            headers=admin_headers,
        )
        if _quantize(balance_after_reverse.get("on_hand_qty_base", 0)) != initial_balance:
            raise VerificationError("purchase invoice reversal did not restore stock balance")

        reversed_again = await _expect_status(
            client,
            "POST",
            f"/api/v1/purchase-invoices/{invoice_id}/reverse",
            200,
            headers=admin_headers,
            json={"reason": "Sprint 14 reversal again"},
        )
        if reversed_again.get("status") != "REVERSED":
            raise VerificationError("second reversal changed purchase invoice status unexpectedly")

        reversal_moves_again = await _list_stock_moves(
            client,
            headers=admin_headers,
            reference_type="purchase_invoice_reverse",
            reference_id=invoice_id,
        )
        if len(reversal_moves_again) != len(reversal_moves):
            raise VerificationError("second reversal created extra stock moves")

        lock_date = invoice_date
        lock_vendor = await _expect_status(
            client,
            "POST",
            "/api/v1/vendors/",
            201,
            headers=admin_headers,
            json={"code": f"VEND-14-LOCK-{uuid.uuid4().hex[:4]}", "name": "Locked Vendor"},
        )
        locked_vendor_id = lock_vendor.get("id")
        if not locked_vendor_id:
            raise VerificationError("locked vendor id missing")

        lock_candidate = await _expect_status(
            client,
            "POST",
            "/api/v1/purchase-invoices/",
            201,
            headers=admin_headers,
            json={
                "vendor_id": locked_vendor_id,
                "invoice_no": f"PI-LOCK-{uuid.uuid4().hex[:6]}",
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
                        "expense_account_id": str(expense_account_id),
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
            f"/api/v1/purchase-invoices/{lock_candidate_id}/post",
            200,
            headers=admin_headers,
        )
        if posted_candidate.get("status") != "POSTED":
            raise VerificationError("pre-lock purchase invoice did not post")

        await _expect_status(
            client,
            "POST",
            "/api/v1/journals/period-locks",
            201,
            headers=admin_headers,
            json={"start_date": lock_date.isoformat(), "end_date": lock_date.isoformat()},
        )

        reverse_locked = await client.post(
            f"/api/v1/purchase-invoices/{lock_candidate_id}/reverse",
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
            "/api/v1/purchase-invoices/",
            201,
            headers=admin_headers,
            json={
                "vendor_id": locked_vendor_id,
                "invoice_no": f"PI-LOCK2-{uuid.uuid4().hex[:6]}",
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
                        "expense_account_id": str(expense_account_id),
                    }
                ],
            },
        )
        locked_draft_id = locked_draft.get("id")
        if not locked_draft_id:
            raise VerificationError("locked draft invoice id missing")

        post_locked = await client.post(
            f"/api/v1/purchase-invoices/{locked_draft_id}/post",
            headers=admin_headers,
        )
        if post_locked.status_code != 409:
            raise VerificationError("posting draft in locked period did not fail")
        if post_locked.json().get("code") != "accounting_period_locked":
            raise VerificationError("locked period error code mismatch on post")

    print("Sprint 14 purchase invoice inventory verification: OK")


def main() -> None:
    try:
        asyncio.run(run())
    except VerificationError as exc:
        print(f"Sprint 14 purchase invoice inventory verification: FAILED - {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
