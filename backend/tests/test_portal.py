from __future__ import annotations

from datetime import date, datetime, timedelta, UTC
from uuid import UUID

import pytest
from httpx import AsyncClient

from app.database import async_session_maker
from app.initial_data import seed_tenant
from app.models.tenant import Tenant
from app.services import portal_service


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _ensure_seeded(tenant_id: str) -> None:
    tenant_uuid = UUID(tenant_id)
    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_uuid)
        await seed_tenant(session, tenant)


@pytest.mark.anyio
async def test_customer_portal_access_isolated(client: AsyncClient, register_owner):
    owner = await register_owner()
    token = owner["tokens"]["access_token"]
    await _ensure_seeded(owner["tenant"]["id"])

    # Two customers
    c1_res = await client.post(
        "/api/v1/customers/",
        json={"code": "PORTAL-ONE", "name": "Portal One", "email": "one@example.com"},
        headers=auth_headers(token),
    )
    assert c1_res.status_code == 201, c1_res.text
    c1 = c1_res.json()

    c2_res = await client.post(
        "/api/v1/customers/",
        json={"code": "PORTAL-TWO", "name": "Portal Two", "email": "two@example.com"},
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
        "/api/v1/portal/link",
        json={"client_id": c1["id"]},
        headers=auth_headers(token),
    )
    assert token_res.status_code == 201, token_res.text
    portal_url = token_res.json()["url"]
    raw_token = portal_url.rstrip("/").split("/")[-1]

    # Access portal via expanded routes
    invoices_res = await client.get(f"/api/v1/portal/{raw_token}/invoices")
    assert invoices_res.status_code == 200, invoices_res.text
    invoices_data = invoices_res.json()
    assert len(invoices_data["invoices"]) == 1
    assert invoices_data["invoices"][0]["customer_id"] == c1["id"]

    payments_res = await client.get(f"/api/v1/portal/{raw_token}/payments")
    assert payments_res.status_code == 200, payments_res.text
    assert payments_res.json()["payments"] == []

    summary_res = await client.get(f"/api/v1/portal/{raw_token}/summary")
    assert summary_res.status_code == 200, summary_res.text
    summary = summary_res.json()
    assert summary["client"]["id"] == c1["id"]

    # Invalid token
    bad_res = await client.get("/api/v1/portal/invalid-token/invoices")
    assert bad_res.status_code == 404


@pytest.mark.anyio
async def test_supplier_portal_routes(client: AsyncClient, register_owner):
    owner = await register_owner()
    token = owner["tokens"]["access_token"]
    await _ensure_seeded(owner["tenant"]["id"])
    tenant_id = UUID(owner["tenant"]["id"])

    supplier_res = await client.post(
        "/api/v1/suppliers/",
        json={
            "code": "PORTAL-SUP",
            "name": "Portal Vendor",
            "email": "vendor@example.com",
            "phone": "555-0001",
        },
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

    expires_at = datetime.now(UTC) + timedelta(hours=1)
    async with async_session_maker() as session:
        raw_token, _ = await portal_service.create_portal_token_for_supplier(
            session, tenant_id, UUID(supplier["id"]), expires_at
        )

    cross_res = await client.get(f"/api/v1/portal/{raw_token}/summary")
    assert cross_res.status_code == 403


@pytest.mark.anyio
async def test_customer_portal_invoices_pagination(client: AsyncClient, register_owner):
    owner = await register_owner(slug="portal-page")
    token = owner["tokens"]["access_token"]
    headers = auth_headers(token)
    await _ensure_seeded(owner["tenant"]["id"])

    customer_res = await client.post(
        "/api/v1/customers/",
        json={"code": "PORTAL-PAGE", "name": "Paged Customer", "email": "paged@example.com"},
        headers=headers,
    )
    assert customer_res.status_code == 201, customer_res.text
    customer = customer_res.json()

    invoice_payload = {
        "issue_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "status": "SENT",
        "currency": "USD",
        "items": [{"description": "Paged item", "quantity": "1", "unit_price": "5.00", "tax_rate": "0", "line_total": "5.00"}],
    }
    for i in range(6):
        payload = {**invoice_payload, "customer_id": customer["id"]}
        payload["items"][0]["description"] = f"Paged item {i + 1}"
        response = await client.post("/api/v1/invoices/", json=payload, headers=headers)
        assert response.status_code == 201, response.text

    token_res = await client.post(
        "/api/v1/portal/link",
        json={"client_id": customer["id"]},
        headers=headers,
    )
    assert token_res.status_code == 201, token_res.text
    portal_url = token_res.json()["url"]
    raw_token = portal_url.rstrip("/").split("/")[-1]

    second_page = await client.get(
        f"/api/v1/portal/{raw_token}/invoices", params={"page": 2, "page_size": 2}
    )
    assert second_page.status_code == 200, second_page.text
    data = second_page.json()
    assert data["page"] == 2
    assert data["page_size"] == 2
    assert data["total"] >= 6
    assert data["pages"] >= 3
    assert len(data["invoices"]) == 2

    last_page = await client.get(
        f"/api/v1/portal/{raw_token}/invoices", params={"page": 3, "page_size": 2}
    )
    assert last_page.status_code == 200, last_page.text
    last_data = last_page.json()
    assert last_data["page"] == last_data["pages"]
    assert len(last_data["invoices"]) == 2


@pytest.mark.anyio
async def test_customer_portal_is_tenant_scoped(client: AsyncClient, register_owner):
    owner_a = await register_owner(slug="portal-tenant-a")
    headers_a = auth_headers(owner_a["tokens"]["access_token"])
    c_a = (await client.post(
        "/api/v1/customers/",
        json={"code": "PORTAL-A", "name": "Portal A"},
        headers=headers_a,
    )).json()
    await client.post(
        "/api/v1/invoices/",
        json={
            "customer_id": c_a["id"],
            "issue_date": date.today().isoformat(),
            "due_date": date.today().isoformat(),
            "status": "SENT",
            "currency": "USD",
            "items": [{"description": "Tenant A", "quantity": "1", "unit_price": "1.00", "tax_rate": "0", "line_total": "1.00"}],
        },
        headers=headers_a,
    )

    owner_b = await register_owner(slug="portal-tenant-b")
    headers_b = auth_headers(owner_b["tokens"]["access_token"])
    c_b = (await client.post(
        "/api/v1/customers/",
        json={"code": "PORTAL-B", "name": "Portal B"},
        headers=headers_b,
    )).json()

    token_res = await client.post(
        "/api/v1/portal/link", json={"client_id": c_b["id"]}, headers=headers_b
    )
    assert token_res.status_code == 201, token_res.text
    portal_url = token_res.json()["url"]
    raw_token = portal_url.rstrip("/").split("/")[-1]

    response = await client.get(f"/api/v1/portal/{raw_token}/invoices")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 0
    assert data["invoices"] == []
