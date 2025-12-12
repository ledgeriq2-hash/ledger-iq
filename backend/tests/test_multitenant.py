from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_tenant_isolation(client: AsyncClient, register_owner):
    owner_a = await register_owner(slug=f"a-{uuid.uuid4().hex[:6]}", email=f"a{uuid.uuid4().hex[:6]}@example.com")
    token_a = owner_a["tokens"]["access_token"]

    owner_b = await register_owner(slug=f"b-{uuid.uuid4().hex[:6]}", email=f"b{uuid.uuid4().hex[:6]}@example.com")
    token_b = owner_b["tokens"]["access_token"]

    cust_a = (
        await client.post("/api/v1/customers/", json={"name": "Cust A", "email": "a@example.com"}, headers=auth_headers(token_a))
    ).json()
    cust_b = (
        await client.post("/api/v1/customers/", json={"name": "Cust B", "email": "b@example.com"}, headers=auth_headers(token_b))
    ).json()

    res1 = await client.get(f"/api/v1/customers/{cust_b['id']}", headers=auth_headers(token_a))
    assert res1.status_code in (403, 404)

    res2 = await client.get(f"/api/v1/customers/{cust_a['id']}", headers=auth_headers(token_b))
    assert res2.status_code in (403, 404)

    list_a = await client.get("/api/v1/customers/", headers=auth_headers(token_a))
    list_b = await client.get("/api/v1/customers/", headers=auth_headers(token_b))
    ids_a = {c["id"] for c in list_a.json()["items"]}
    ids_b = {c["id"] for c in list_b.json()["items"]}
    assert cust_a["id"] in ids_a and cust_a["id"] not in ids_b
    assert cust_b["id"] in ids_b and cust_b["id"] not in ids_a
