from __future__ import annotations

import uuid
from datetime import date

import pytest
from httpx import AsyncClient

from app.initial_data import seed_tenant
from app.database import async_session_maker
from app.models.tenant import Tenant


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def ensure_seed(tenant_id: uuid.UUID) -> None:
    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_id)
        await seed_tenant(session, tenant)


@pytest.mark.anyio
async def test_full_user_journey(client: AsyncClient, register_owner):
    owner = await register_owner()
    token = owner["tokens"]["access_token"]
    tenant_id = uuid.UUID(owner["tenant"]["id"])
    await ensure_seed(tenant_id)

    # Health check
    health = await client.get("/health")
    assert health.status_code == 200

    # Create customer
    cust_payload = {
        "code": "JOURNEY-001",
        "name": "Journey Customer",
        "email": "journey@example.com",
        "phone": "555-0100",
    }
    cust_res = await client.post("/api/v1/customers/", json=cust_payload, headers=auth_headers(token))
    assert cust_res.status_code == 201, cust_res.text
    customer = cust_res.json()

    # Create product
    prod_payload = {"name": "Journey Product", "sku": "JP-1", "unit_price": "250.00", "is_service": True}
    prod_res = await client.post("/api/v1/products/", json=prod_payload, headers=auth_headers(token))
    assert prod_res.status_code == 201, prod_res.text
    product = prod_res.json()

    # Paid invoice
    paid_payload = {
        "customer_id": customer["id"],
        "issue_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "status": "PAID",
        "currency": "USD",
        "items": [
            {
                "product_id": product["id"],
                "description": "Paid item",
                "quantity": "1",
                "unit_price": "250.00",
                "tax_rate": "0",
                "line_total": "250.00",
            }
        ],
    }
    paid_res = await client.post("/api/v1/invoices/", json=paid_payload, headers=auth_headers(token))
    assert paid_res.status_code == 201, paid_res.text
    paid_invoice = paid_res.json()

    # Unpaid invoice
    unpaid_payload = {
        "customer_id": customer["id"],
        "issue_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "status": "SENT",
        "currency": "USD",
        "items": [
            {
                "product_id": product["id"],
                "description": "Unpaid item",
                "quantity": "1",
                "unit_price": "150.00",
                "tax_rate": "0",
                "line_total": "150.00",
            }
        ],
    }
    unpaid_res = await client.post("/api/v1/invoices/", json=unpaid_payload, headers=auth_headers(token))
    assert unpaid_res.status_code == 201, unpaid_res.text

    # Record payment on paid invoice
    pay_payload = {
        "invoice_id": paid_invoice["id"],
        "customer_id": customer["id"],
        "amount": "250.00",
        "method": "card",
    }
    pay_res = await client.post("/api/v1/payments/", json=pay_payload, headers=auth_headers(token))
    assert pay_res.status_code == 201, pay_res.text

    # Journal entries
    je_res = await client.get("/api/v1/journal-entries/", headers=auth_headers(token))
    assert je_res.status_code == 200, je_res.text
    assert len(je_res.json().get("items", [])) >= 1

    # Trial balance (requires as_of_date)
    tb_res = await client.get(
        "/api/v1/reports/trial-balance",
        params={"as_of_date": date.today().isoformat()},
        headers=auth_headers(token),
    )
    assert tb_res.status_code == 200, tb_res.text
    tb_data = tb_res.json()
    assert "data" in tb_data
    accounts = tb_data["data"].get("accounts", [])
    assert len(accounts) >= 1
    totals = tb_data["data"].get("totals", {})
    assert totals.get("debit") == totals.get("credit")
