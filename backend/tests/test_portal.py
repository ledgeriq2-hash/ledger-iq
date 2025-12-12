from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_customer_portal_access_isolated(client: AsyncClient, register_owner):
    owner = await register_owner()
    token = owner["tokens"]["access_token"]

    # Two customers
    c1_res = await client.post(
        "/api/v1/customers/",
        json={"name": "Portal One", "email": "one@example.com"},
        headers=auth_headers(token),
    )
    assert c1_res.status_code == 201, c1_res.text
    c1 = c1_res.json()

    c2_res = await client.post(
        "/api/v1/customers/",
        json={"name": "Portal Two", "email": "two@example.com"},
        headers=auth_headers(token),
    )
    assert c2_res.status_code == 201, c2_res.text
    c2 = c2_res.json()

    # Invoice for customer 1
    inv1_payload = {
        "customer_id": c1["id"],
        "issue_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "status": "SENT",
        "currency": "USD",
        "items": [{"description": "C1 item", "quantity": "1", "unit_price": "10.00", "tax_rate": "0", "line_total": "10.00"}],
    }
    inv1_res = await client.post("/api/v1/invoices/", json=inv1_payload, headers=auth_headers(token))
    assert inv1_res.status_code == 201, inv1_res.text

    # Invoice for customer 2
    inv2_payload = {
        "customer_id": c2["id"],
        "issue_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "status": "SENT",
        "currency": "USD",
        "items": [{"description": "C2 item", "quantity": "1", "unit_price": "20.00", "tax_rate": "0", "line_total": "20.00"}],
    }
    inv2_res = await client.post("/api/v1/invoices/", json=inv2_payload, headers=auth_headers(token))
    assert inv2_res.status_code == 201, inv2_res.text

    # Portal token for customer 1
    token_res = await client.post(
        "/api/v1/portal/customer/token",
        json={"customer_id": c1["id"]},
        headers=auth_headers(token),
    )
    assert token_res.status_code == 201, token_res.text
    portal_url = token_res.json()["url"]
    raw_token = portal_url.rstrip("/").split("/")[-1]

    # Access portal via expanded routes
    invoices_res = await client.get(f"/api/v1/portal/customer/{raw_token}/invoices")
    assert invoices_res.status_code == 200, invoices_res.text
    invoices_data = invoices_res.json()
    assert len(invoices_data["invoices"]) == 1
    assert invoices_data["invoices"][0]["customer_id"] == c1["id"]

    payments_res = await client.get(f"/api/v1/portal/customer/{raw_token}/payments")
    assert payments_res.status_code == 200, payments_res.text
    assert payments_res.json()["payments"] == []

    settings_res = await client.get(f"/api/v1/portal/customer/{raw_token}/settings")
    assert settings_res.status_code == 200, settings_res.text
    assert settings_res.json()["notifications"] is True
    assert settings_res.json()["language"] == "en"

    overview_res = await client.get(f"/api/v1/portal/customer/{raw_token}")
    assert overview_res.status_code == 200, overview_res.text
    overview = overview_res.json()
    assert overview["customer"]["id"] == c1["id"]
    assert overview["settings"]["language"] == "en"

    # Invalid token
    bad_res = await client.get("/api/v1/portal/customer/invalid-token/invoices")
    assert bad_res.status_code == 404


@pytest.mark.anyio
async def test_supplier_portal_routes(client: AsyncClient, register_owner):
    owner = await register_owner()
    token = owner["tokens"]["access_token"]

    supplier_res = await client.post(
        "/api/v1/suppliers/",
        json={"name": "Portal Vendor", "email": "vendor@example.com", "phone": "555-0001"},
        headers=auth_headers(token),
    )
    assert supplier_res.status_code == 201, supplier_res.text
    supplier = supplier_res.json()

    expense_res = await client.post(
        "/api/v1/expenses/",
        json={
            "supplier_id": supplier["id"],
            "category": "Services",
            "amount": "150.00",
            "currency": "USD",
            "expense_date": date.today().isoformat(),
            "description": "Portal test expense",
        },
        headers=auth_headers(token),
    )
    assert expense_res.status_code == 201, expense_res.text

    token_res = await client.post(
        "/api/v1/portal/supplier/token",
        json={"supplier_id": supplier["id"]},
        headers=auth_headers(token),
    )
    assert token_res.status_code == 201, token_res.text
    portal_url = token_res.json()["url"]
    raw_token = portal_url.rstrip("/").split("/")[-1]

    orders_res = await client.get(f"/api/v1/portal/supplier/{raw_token}/orders")
    assert orders_res.status_code == 200, orders_res.text
    orders = orders_res.json()["orders"]
    assert len(orders) == 1
    assert orders[0]["reference"] == "Portal test expense"

    payments_res = await client.get(f"/api/v1/portal/supplier/{raw_token}/payments")
    assert payments_res.status_code == 200, payments_res.text
    payments = payments_res.json()["payments"]
    assert len(payments) == 1
    assert payments[0]["amount"] == "150.00"

    settings_res = await client.get(f"/api/v1/portal/supplier/{raw_token}/settings")
    assert settings_res.status_code == 200, settings_res.text

    overview_res = await client.get(f"/api/v1/portal/supplier/{raw_token}")
    assert overview_res.status_code == 200, overview_res.text
    overview = overview_res.json()
    assert overview["supplier"]["id"] == supplier["id"]
    assert overview["orders"][0]["id"] == orders[0]["id"]

    bad_res = await client.get("/api/v1/portal/supplier/invalid-token/orders")
    assert bad_res.status_code == 404

    cross_res = await client.get(f"/api/v1/portal/customer/{raw_token}/invoices")
    assert cross_res.status_code == 403
