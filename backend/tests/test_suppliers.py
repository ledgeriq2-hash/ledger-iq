from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session_maker
from app.models.audit_log import AuditLog


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _create_supplier(client: AsyncClient, token: str, name: str = "Vendor") -> dict:
    payload = {
        "code": f"{name[:6].upper()}-{uuid.uuid4().hex[:6]}",
        "name": name,
        "email": f"{name.lower()}@example.com",
        "phone": "555-1000",
        "address": "123 Road",
    }
    response = await client.post("/api/v1/suppliers/", json=payload, headers=_auth_headers(token))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_create_supplier(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    supplier = await _create_supplier(client, token)
    assert supplier["name"] == "Vendor"
    assert supplier["email"] == "vendor@example.com"


@pytest.mark.anyio
async def test_update_supplier(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    supplier = await _create_supplier(client, token)
    update_payload = {"name": "Updated Vendor", "address": "456 Avenue"}
    response = await client.patch(
        f"/api/v1/suppliers/{supplier['id']}",
        json=update_payload,
        headers=_auth_headers(token),
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["name"] == "Updated Vendor"
    assert updated["address"] == "456 Avenue"


@pytest.mark.anyio
async def test_supplier_code_uniqueness(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    payload = {
        "code": "DUP-001",
        "name": "Dup Supplier",
        "email": "dup@example.com",
    }
    first = await client.post("/api/v1/suppliers/", json=payload, headers=_auth_headers(token))
    assert first.status_code == 201, first.text
    second = await client.post("/api/v1/suppliers/", json=payload, headers=_auth_headers(token))
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "supplier_code_exists"


@pytest.mark.anyio
async def test_tenant_cannot_access_another_tenants_supplier(client: AsyncClient, register_owner):
    auth_a = await register_owner()
    token_a = auth_a["tokens"]["access_token"]
    supplier_a = await _create_supplier(client, token_a, name="TenantA")

    auth_b = await register_owner()
    token_b = auth_b["tokens"]["access_token"]

    get_response = await client.get(
        f"/api/v1/suppliers/{supplier_a['id']}",
        headers=_auth_headers(token_b),
    )
    assert get_response.status_code == 404

    update_response = await client.patch(
        f"/api/v1/suppliers/{supplier_a['id']}",
        json={"name": "Hacker"},
        headers=_auth_headers(token_b),
    )
    assert update_response.status_code == 404

    delete_response = await client.delete(
        f"/api/v1/suppliers/{supplier_a['id']}",
        headers=_auth_headers(token_b),
    )
    assert delete_response.status_code == 404


@pytest.mark.anyio
async def test_soft_delete_blocks_patch_and_list(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    supplier = await _create_supplier(client, token, name="DeleteMe")
    delete_res = await client.delete(
        f"/api/v1/suppliers/{supplier['id']}",
        headers=_auth_headers(token),
    )
    assert delete_res.status_code == 204, delete_res.text

    list_res = await client.get("/api/v1/suppliers/", headers=_auth_headers(token))
    assert list_res.status_code == 200, list_res.text
    ids = {item["id"] for item in list_res.json()["items"]}
    assert supplier["id"] not in ids

    patch_res = await client.patch(
        f"/api/v1/suppliers/{supplier['id']}",
        json={"name": "Should Fail"},
        headers=_auth_headers(token),
    )
    assert patch_res.status_code == 409
    assert patch_res.json()["code"] == "supplier_deleted"


@pytest.mark.anyio
async def test_list_include_deleted(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    supplier_a = await _create_supplier(client, token, name="Active")
    supplier_b = await _create_supplier(client, token, name="ToDelete")

    delete_res = await client.delete(
        f"/api/v1/suppliers/{supplier_b['id']}",
        headers=_auth_headers(token),
    )
    assert delete_res.status_code == 204, delete_res.text

    list_default = await client.get("/api/v1/suppliers/", headers=_auth_headers(token))
    assert list_default.status_code == 200
    default_ids = {item["id"] for item in list_default.json()["items"]}
    assert supplier_a["id"] in default_ids
    assert supplier_b["id"] not in default_ids

    list_all = await client.get(
        "/api/v1/suppliers/",
        params={"include_deleted": "true"},
        headers=_auth_headers(token),
    )
    assert list_all.status_code == 200
    all_ids = {item["id"] for item in list_all.json()["items"]}
    assert supplier_a["id"] in all_ids
    assert supplier_b["id"] in all_ids


@pytest.mark.anyio
async def test_supplier_audit_logs_created(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]
    tenant_id = uuid.UUID(auth["tenant"]["id"])

    supplier = await _create_supplier(client, token, name="AuditMe")
    update_res = await client.patch(
        f"/api/v1/suppliers/{supplier['id']}",
        json={"phone": "555-9999"},
        headers=_auth_headers(token),
    )
    assert update_res.status_code == 200, update_res.text

    deactivate_res = await client.post(
        f"/api/v1/suppliers/{supplier['id']}/deactivate",
        headers=_auth_headers(token),
    )
    assert deactivate_res.status_code == 200, deactivate_res.text

    reactivate_res = await client.post(
        f"/api/v1/suppliers/{supplier['id']}/reactivate",
        headers=_auth_headers(token),
    )
    assert reactivate_res.status_code == 200, reactivate_res.text

    delete_res = await client.delete(
        f"/api/v1/suppliers/{supplier['id']}",
        headers=_auth_headers(token),
    )
    assert delete_res.status_code == 204, delete_res.text

    async with async_session_maker() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.tenant_id == tenant_id, AuditLog.table_name == "suppliers")
        )
        actions = {log.action for log in result.scalars().all()}
        assert "SUPPLIER.CREATE" in actions
        assert "SUPPLIER.UPDATE" in actions
        assert "SUPPLIER.DEACTIVATE" in actions
        assert "SUPPLIER.REACTIVATE" in actions
        assert "SUPPLIER.SOFT_DELETE" in actions

