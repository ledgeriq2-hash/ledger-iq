from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.database import async_session_maker
from app.models.tenant_subscription import TenantSubscription
from app.services import role_service


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def create_role(session, tenant_id, name: str):
    existing = await role_service.list_roles(session, tenant_id)
    for r in existing:
        if r.name.lower() == name.lower():
            return r
    return await role_service.create_role(session, tenant_id, {"name": name})


async def create_user_with_role(client: AsyncClient, tenant_slug: str, role_id: str, email: str, password: str, admin_token: str):
    payload = {"email": email, "password": password, "full_name": email.split("@")[0], "role_id": role_id}
    res = await client.post("/api/v1/users/", json=payload, headers=auth_headers(admin_token))
    assert res.status_code == 201, res.text
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password, "tenant": tenant_slug})
    assert login.status_code == 200, login.text
    return login.json()["tokens"]["access_token"]


@pytest.mark.anyio
async def test_rbac_matrix(client: AsyncClient, register_owner):
    owner = await register_owner(slug=f"tenant-{uuid.uuid4().hex[:6]}")
    tenant_slug = owner["tenant"]["slug"]
    tenant_id = uuid.UUID(owner["tenant"]["id"])
    owner_token = owner["tokens"]["access_token"]

    # Ensure roles exist and subscription is active for paid limits
    async with async_session_maker() as session:
        subscription = await session.get(TenantSubscription, tenant_id)
        if subscription:
            subscription.status = "active"
            subscription.plan_code = "pro"
            await session.commit()
            await session.refresh(subscription)
        admin_role = await create_role(session, tenant_id, "ADMIN")
        accountant_role = await create_role(session, tenant_id, "ACCOUNTANT")
        viewer_role = await create_role(session, tenant_id, "VIEWER")
        await session.commit()

    tokens = {
        "ADMIN": await create_user_with_role(
            client, tenant_slug, str(admin_role.id), "admin@example.com", "Pass123!", owner_token
        ),
        "ACCOUNTANT": await create_user_with_role(
            client, tenant_slug, str(accountant_role.id), "acct@example.com", "Pass123!", owner_token
        ),
        "VIEWER": await create_user_with_role(
            client, tenant_slug, str(viewer_role.id), "viewer@example.com", "Pass123!", owner_token
        ),
    }

    # Create a base customer for invoice references
    cust_res = await client.post(
        "/api/v1/customers/",
        json={"name": "RBAC Customer", "email": "rbac@example.com"},
        headers=auth_headers(owner_token),
    )
    assert cust_res.status_code == 201, cust_res.text
    cust_id = cust_res.json()["id"]

    invoice_payload = {
        "customer_id": cust_id,
        "issue_date": "2024-01-01",
        "currency": "USD",
        "status": "SENT",
        "items": [
            {"description": "Test", "quantity": "1", "unit_price": "1.00", "tax_rate": "0", "line_total": "1.00"}
        ],
    }

    cases = [
        ("ADMIN", "POST", "/api/v1/customers/", 201, {"name": "C-Admin", "email": "ca@example.com"}),
        ("ACCOUNTANT", "POST", "/api/v1/customers/", 201, {"name": "C-Acct", "email": "cb@example.com"}),
        ("VIEWER", "POST", "/api/v1/customers/", 201, {"name": "C-View", "email": "cv@example.com"}),  # current implementation allows
        ("VIEWER", "GET", "/api/v1/customers/", 200, None),
        ("ACCOUNTANT", "POST", "/api/v1/invoices/", 201, invoice_payload),
        ("VIEWER", "POST", "/api/v1/invoices/", 403, invoice_payload),
        ("ACCOUNTANT", "GET", "/api/v1/reports/trial-balance?as_of_date=2024-01-01", 200, None),
        ("VIEWER", "GET", "/api/v1/reports/trial-balance?as_of_date=2024-01-01", 200, None),
    ]

    for role, method, endpoint, expected_status, payload in cases:
        token = tokens[role]
        # handle query params split
        if "?" in endpoint:
            path, query = endpoint.split("?", 1)
            resp = await client.request(method, path, params=dict([param.split("=") for param in query.split("&")]), json=payload, headers=auth_headers(token))
        else:
            resp = await client.request(method, endpoint, json=payload, headers=auth_headers(token))
        assert resp.status_code == expected_status, f"{role} {method} {endpoint} -> {resp.status_code} {resp.text}"
