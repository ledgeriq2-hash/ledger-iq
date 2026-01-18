from __future__ import annotations

import uuid
from datetime import date

import pytest
from httpx import AsyncClient

from app.accounting.use_cases.lock_accounting_period import lock_accounting_period
from app.database import async_session_maker
from app.models.chart_of_account import AccountType, ChartOfAccount
from app.models.tenant import Tenant
from app.models.treasury import Treasury


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_customer(client: AsyncClient, token: str, name: str = "Customer") -> dict:
    payload = {
        "code": f"{name[:3].upper()}-{uuid.uuid4().hex[:6]}",
        "name": name,
        "email": f"{name.lower()}@example.com",
    }
    response = await client.post("/api/v1/customers/", json=payload, headers=_auth_headers(token))
    assert response.status_code == 201, response.text
    return response.json()


async def _create_supplier(client: AsyncClient, token: str, name: str = "Supplier") -> dict:
    payload = {
        "code": f"{name[:3].upper()}-{uuid.uuid4().hex[:6]}",
        "name": name,
        "email": f"{name.lower()}@example.com",
    }
    response = await client.post("/api/v1/suppliers/", json=payload, headers=_auth_headers(token))
    assert response.status_code == 201, response.text
    return response.json()


async def _create_employee(client: AsyncClient, token: str, name: str = "Employee") -> dict:
    payload = {
        "code": f"{name[:3].upper()}-{uuid.uuid4().hex[:6]}",
        "name": name,
        "email": f"{name.lower()}@example.com",
    }
    response = await client.post("/api/v1/employees/", json=payload, headers=_auth_headers(token))
    assert response.status_code == 201, response.text
    return response.json()


async def _create_product(client: AsyncClient, token: str, name: str = "Widget") -> dict:
    payload = {
        "name": name,
        "sku": f"SKU-{uuid.uuid4().hex[:6]}",
        "unit_price": "25.00",
        "cost_price": "10.00",
        "stock_quantity": "5.00",
        "is_service": False,
    }
    response = await client.post("/api/v1/products/", json=payload, headers=_auth_headers(token))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
async def auth_context(register_owner):
    auth = await register_owner()
    return {
        "token": auth["tokens"]["access_token"],
        "tenant_id": uuid.UUID(auth["tenant"]["id"]),
        "user_id": uuid.UUID(auth["user"]["id"]),
    }


@pytest.fixture
async def coa_mapping(auth_context):
    tenant_id = auth_context["tenant_id"]
    async with async_session_maker() as session:
        ar = ChartOfAccount(code="1100", name="Accounts Receivable", type=AccountType.ASSET, tenant_id=tenant_id)
        revenue = ChartOfAccount(code="4000", name="Revenue", type=AccountType.REVENUE, tenant_id=tenant_id)
        cash = ChartOfAccount(code="1000", name="Cash", type=AccountType.ASSET, tenant_id=tenant_id)
        payables = ChartOfAccount(code="2000", name="Payables", type=AccountType.LIABILITY, tenant_id=tenant_id)
        expense = ChartOfAccount(code="5000", name="Expenses", type=AccountType.EXPENSE, tenant_id=tenant_id)
        session.add_all([ar, revenue, cash, payables, expense])
        await session.flush()

        tenant = await session.get(Tenant, tenant_id)
        tenant.settings_json = {
            "chart_of_accounts_mapping": {
                "accounts_receivable_account_id": str(ar.id),
                "revenue_account_id": str(revenue.id),
                "cash_account_id": str(cash.id),
                "payables_account_id": str(payables.id),
                "expense_account_id": str(expense.id),
                "cashflow_account_ids": [str(cash.id)],
            }
        }
        await session.commit()

    return {
        "ar": ar.id,
        "revenue": revenue.id,
        "cash": cash.id,
        "payables": payables.id,
        "expense": expense.id,
    }


@pytest.fixture
async def treasury_id(auth_context):
    tenant_id = auth_context["tenant_id"]
    async with async_session_maker() as session:
        treasury = Treasury(tenant_id=tenant_id, type="cash", name="Main Treasury")
        session.add(treasury)
        await session.commit()
        await session.refresh(treasury)
        return treasury.id


@pytest.mark.anyio
async def test_treasury_receipt_reverse_adjust(client: AsyncClient, auth_context, coa_mapping, treasury_id):
    token = auth_context["token"]
    customer = await _create_customer(client, token, name="ReceiptCo")
    receipt_payload = {
        "amount": "120.00",
        "customer_id": customer["id"],
        "reference_type": "treasury_receipt",
        "reference_id": str(uuid.uuid4()),
        "description": "Initial receipt",
        "entry_date": date.today().isoformat(),
    }
    receipt_resp = await client.post(
        f"/api/v1/treasury/{treasury_id}/movements/receipt",
        json=receipt_payload,
        headers=_auth_headers(token),
    )
    assert receipt_resp.status_code == 200, receipt_resp.text
    movement = receipt_resp.json()

    reverse_resp = await client.post(
        f"/api/v1/treasury/movements/{movement['id']}/reverse",
        json={"reason": "Test reversal"},
        headers=_auth_headers(token),
    )
    assert reverse_resp.status_code == 200, reverse_resp.text

    adjust_payload = {
        "reason": "Adjustment test",
        "lines": [
            {"account_id": str(coa_mapping["cash"]), "debit": "5.00", "credit": "0"},
            {"account_id": str(coa_mapping["ar"]), "debit": "0", "credit": "5.00"},
        ],
    }
    adjust_resp = await client.post(
        f"/api/v1/treasury/movements/{movement['id']}/adjust",
        json=adjust_payload,
        headers={"Idempotency-Key": uuid.uuid4().hex, **_auth_headers(token)},
    )
    assert adjust_resp.status_code == 200, adjust_resp.text


@pytest.mark.anyio
async def test_account_mapping_missing_returns_422(client: AsyncClient, auth_context, treasury_id):
    token = auth_context["token"]
    customer = await _create_customer(client, token, name="MapMissing")
    payload = {
        "amount": "50.00",
        "customer_id": customer["id"],
        "reference_type": "treasury_receipt",
        "reference_id": str(uuid.uuid4()),
    }
    response = await client.post(
        f"/api/v1/treasury/{treasury_id}/movements/receipt",
        json=payload,
        headers=_auth_headers(token),
    )
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "account_mapping_missing"
    assert body["message"] == "Account mapping is missing required keys"


@pytest.mark.anyio
async def test_period_lock_blocks_treasury_movement(client: AsyncClient, auth_context, coa_mapping, treasury_id):
    token = auth_context["token"]
    tenant_id = auth_context["tenant_id"]
    actor_id = auth_context["user_id"]
    today = date.today()
    async with async_session_maker() as session:
        await lock_accounting_period(
            session,
            tenant_id=tenant_id,
            start_date=today,
            end_date=today,
            actor_id=actor_id,
        )

    customer = await _create_customer(client, token, name="Locked")
    payload = {
        "amount": "75.00",
        "customer_id": customer["id"],
        "reference_type": "treasury_receipt",
        "reference_id": str(uuid.uuid4()),
        "entry_date": today.isoformat(),
    }
    response = await client.post(
        f"/api/v1/treasury/{treasury_id}/movements/receipt",
        json=payload,
        headers=_auth_headers(token),
    )
    assert response.status_code == 409, response.text
    body = response.json()
    assert body["code"] == "accounting_period_locked"


@pytest.mark.anyio
async def test_inactive_supplier_blocked(client: AsyncClient, auth_context, coa_mapping, treasury_id):
    token = auth_context["token"]
    supplier = await _create_supplier(client, token, name="BlockedSupplier")
    deactivate = await client.post(
        f"/api/v1/suppliers/{supplier['id']}/deactivate",
        headers=_auth_headers(token),
    )
    assert deactivate.status_code == 200, deactivate.text

    payload = {
        "amount": "33.00",
        "supplier_id": supplier["id"],
        "reference_type": "supplier_payment",
        "reference_id": str(uuid.uuid4()),
    }
    response = await client.post(
        f"/api/v1/treasury/{treasury_id}/movements/supplier-payment",
        json=payload,
        headers=_auth_headers(token),
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "supplier_inactive"


@pytest.mark.anyio
async def test_invoice_payment_expense_and_reports(client: AsyncClient, auth_context, coa_mapping, treasury_id):
    token = auth_context["token"]
    customer = await _create_customer(client, token, name="InvoiceCo")
    supplier = await _create_supplier(client, token, name="ExpenseCo")
    employee = await _create_employee(client, token, name="PayrollCo")
    product = await _create_product(client, token, name="Widget")

    invoice_payload = {
        "customer_id": customer["id"],
        "issue_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "currency": "USD",
        "items": [
            {
                "product_id": product["id"],
                "description": "Widget",
                "quantity": "2",
                "unit_price": "25.00",
                "tax_rate": "0",
            }
        ],
    }
    create_invoice = await client.post(
        "/api/v1/invoices/",
        json=invoice_payload,
        headers=_auth_headers(token),
    )
    assert create_invoice.status_code == 201, create_invoice.text
    invoice = create_invoice.json()

    post_invoice = await client.post(
        f"/api/v1/invoices/{invoice['id']}/post",
        headers=_auth_headers(token),
    )
    assert post_invoice.status_code == 200, post_invoice.text

    pay_invoice = await client.post(
        f"/api/v1/invoices/{invoice['id']}/payments",
        json={"amount": "10.00", "method": "cash"},
        headers=_auth_headers(token),
    )
    assert pay_invoice.status_code == 200, pay_invoice.text

    create_payment = await client.post(
        "/api/v1/payments/",
        json={
            "customer_id": customer["id"],
            "invoice_id": invoice["id"],
            "amount": "5.00",
            "method": "card",
        },
        headers=_auth_headers(token),
    )
    assert create_payment.status_code == 201, create_payment.text

    expense_payload = {
        "supplier_id": supplier["id"],
        "category": "supplies",
        "amount": "40.00",
        "currency": "USD",
        "expense_date": date.today().isoformat(),
        "description": "Office supplies",
        "product_id": product["id"],
        "quantity": "1",
    }
    expense_resp = await client.post(
        "/api/v1/expenses/",
        json=expense_payload,
        headers=_auth_headers(token),
    )
    assert expense_resp.status_code == 201, expense_resp.text

    employee_payment = await client.post(
        f"/api/v1/treasury/{treasury_id}/movements/employee-payment",
        json={
            "amount": "60.00",
            "employee_id": employee["id"],
            "reference_type": "employee_payment",
            "reference_id": str(uuid.uuid4()),
        },
        headers=_auth_headers(token),
    )
    assert employee_payment.status_code == 200, employee_payment.text

    report_resp = await client.get(
        "/api/v1/reports/client-statement",
        params={"client_id": customer["id"]},
        headers=_auth_headers(token),
    )
    assert report_resp.status_code == 200, report_resp.text

    treasury_report = await client.get(
        "/api/v1/reports/treasury",
        params={"treasury_id": str(treasury_id)},
        headers=_auth_headers(token),
    )
    assert treasury_report.status_code == 200, treasury_report.text

    trial_balance = await client.post(
        "/api/v1/reports/run",
        json={"report_type": "trial_balance", "params": {"as_of_date": date.today().isoformat()}},
        headers=_auth_headers(token),
    )
    assert trial_balance.status_code == 200, trial_balance.text
