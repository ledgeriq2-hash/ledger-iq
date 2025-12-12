from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_wrong_credentials(client: AsyncClient):
    res = await client.post("/api/v1/auth/login", json={"email": "none@example.com", "password": "bad", "tenant": "none"})
    assert res.status_code in (400, 401, 403, 404)


@pytest.mark.anyio
async def test_protected_without_token(client: AsyncClient):
    res = await client.get("/api/v1/customers/")
    assert res.status_code in (400, 401, 403)


@pytest.mark.anyio
async def test_create_customer_invalid_payload(client: AsyncClient, register_owner):
    owner = await register_owner()
    token = owner["tokens"]["access_token"]
    res = await client.post("/api/v1/customers/", json={"email": "missing-name"}, headers=auth_headers(token))
    assert res.status_code in (400, 422)


@pytest.mark.anyio
async def test_invalid_portal_token(client: AsyncClient):
    res = await client.get("/api/v1/portal/customer/not-a-real-token")
    assert res.status_code == 404


@pytest.mark.anyio
async def test_invoice_not_found(client: AsyncClient, register_owner):
    owner = await register_owner()
    token = owner["tokens"]["access_token"]
    res = await client.get(f"/api/v1/invoices/{uuid.uuid4()}", headers=auth_headers(token))
    assert res.status_code == 404
