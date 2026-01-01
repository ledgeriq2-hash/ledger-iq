from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.exceptions import AppException
from app.database import async_session_maker
from app.models.audit_log import AuditLog
from app.services import employee_service


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _create_employee(client: AsyncClient, token: str, name: str = "Worker") -> dict:
    payload = {
        "code": f"{name[:6].upper()}-{uuid.uuid4().hex[:6]}",
        "name": name,
        "email": f"{name.lower()}@example.com",
        "phone": "555-2000",
        "address": "456 Street",
    }
    response = await client.post("/api/v1/employees/", json=payload, headers=_auth_headers(token))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_create_employee(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    employee = await _create_employee(client, token)
    assert employee["name"] == "Worker"
    assert employee["email"] == "worker@example.com"


@pytest.mark.anyio
async def test_update_employee(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    employee = await _create_employee(client, token)
    update_payload = {"name": "Updated Worker", "address": "789 Avenue"}
    response = await client.patch(
        f"/api/v1/employees/{employee['id']}",
        json=update_payload,
        headers=_auth_headers(token),
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["name"] == "Updated Worker"
    assert updated["address"] == "789 Avenue"


@pytest.mark.anyio
async def test_employee_code_uniqueness(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    payload = {
        "code": "EMP-001",
        "name": "Dup Employee",
        "email": "dup@example.com",
    }
    first = await client.post("/api/v1/employees/", json=payload, headers=_auth_headers(token))
    assert first.status_code == 201, first.text
    second = await client.post("/api/v1/employees/", json=payload, headers=_auth_headers(token))
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "employee_code_exists"


@pytest.mark.anyio
async def test_tenant_cannot_access_another_tenants_employee(client: AsyncClient, register_owner):
    auth_a = await register_owner()
    token_a = auth_a["tokens"]["access_token"]
    employee_a = await _create_employee(client, token_a, name="TenantA")

    auth_b = await register_owner()
    token_b = auth_b["tokens"]["access_token"]

    get_response = await client.get(
        f"/api/v1/employees/{employee_a['id']}",
        headers=_auth_headers(token_b),
    )
    assert get_response.status_code == 404

    update_response = await client.patch(
        f"/api/v1/employees/{employee_a['id']}",
        json={"name": "Hacker"},
        headers=_auth_headers(token_b),
    )
    assert update_response.status_code == 404

    delete_response = await client.delete(
        f"/api/v1/employees/{employee_a['id']}",
        headers=_auth_headers(token_b),
    )
    assert delete_response.status_code == 404


@pytest.mark.anyio
async def test_soft_delete_blocks_patch_and_list(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    employee = await _create_employee(client, token, name="DeleteMe")
    delete_res = await client.delete(
        f"/api/v1/employees/{employee['id']}",
        headers=_auth_headers(token),
    )
    assert delete_res.status_code == 204, delete_res.text

    list_res = await client.get("/api/v1/employees/", headers=_auth_headers(token))
    assert list_res.status_code == 200, list_res.text
    ids = {item["id"] for item in list_res.json()["items"]}
    assert employee["id"] not in ids

    patch_res = await client.patch(
        f"/api/v1/employees/{employee['id']}",
        json={"name": "Should Fail"},
        headers=_auth_headers(token),
    )
    assert patch_res.status_code == 409
    assert patch_res.json()["code"] == "employee_deleted"


@pytest.mark.anyio
async def test_list_include_deleted(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    employee_a = await _create_employee(client, token, name="Active")
    employee_b = await _create_employee(client, token, name="ToDelete")

    delete_res = await client.delete(
        f"/api/v1/employees/{employee_b['id']}",
        headers=_auth_headers(token),
    )
    assert delete_res.status_code == 204, delete_res.text

    list_default = await client.get("/api/v1/employees/", headers=_auth_headers(token))
    assert list_default.status_code == 200
    default_ids = {item["id"] for item in list_default.json()["items"]}
    assert employee_a["id"] in default_ids
    assert employee_b["id"] not in default_ids

    list_all = await client.get(
        "/api/v1/employees/",
        params={"include_deleted": "true"},
        headers=_auth_headers(token),
    )
    assert list_all.status_code == 200
    all_ids = {item["id"] for item in list_all.json()["items"]}
    assert employee_a["id"] in all_ids
    assert employee_b["id"] in all_ids


@pytest.mark.anyio
async def test_inactive_and_deleted_employee_block_movements(register_owner):
    auth = await register_owner()
    tenant_id = uuid.UUID(auth["tenant"]["id"])

    async with async_session_maker() as session:
        employee = await employee_service.create_employee(
            session,
            tenant_id,
            {"code": "BLOCK-EMP", "name": "Blocked Employee", "email": "blocked@example.com"},
        )
        await employee_service.deactivate_employee(session, tenant_id, employee.id)
        with pytest.raises(AppException) as exc:
            await employee_service.validate_can_receive_movements(session, tenant_id, employee.id)
        assert exc.value.http_status == 409
        assert exc.value.code == "employee_inactive"

        await employee_service.soft_delete_employee(session, tenant_id, employee.id)
        with pytest.raises(AppException) as exc_deleted:
            await employee_service.validate_can_receive_movements(session, tenant_id, employee.id)
        assert exc_deleted.value.http_status == 409
        assert exc_deleted.value.code == "employee_deleted"


@pytest.mark.anyio
async def test_employee_audit_logs_created(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]
    tenant_id = uuid.UUID(auth["tenant"]["id"])

    employee = await _create_employee(client, token, name="AuditMe")
    update_res = await client.patch(
        f"/api/v1/employees/{employee['id']}",
        json={"phone": "555-9999"},
        headers=_auth_headers(token),
    )
    assert update_res.status_code == 200, update_res.text

    deactivate_res = await client.post(
        f"/api/v1/employees/{employee['id']}/deactivate",
        headers=_auth_headers(token),
    )
    assert deactivate_res.status_code == 200, deactivate_res.text

    reactivate_res = await client.post(
        f"/api/v1/employees/{employee['id']}/reactivate",
        headers=_auth_headers(token),
    )
    assert reactivate_res.status_code == 200, reactivate_res.text

    delete_res = await client.delete(
        f"/api/v1/employees/{employee['id']}",
        headers=_auth_headers(token),
    )
    assert delete_res.status_code == 204, delete_res.text

    async with async_session_maker() as session:
        result = await session.execute(
            select(AuditLog).where(AuditLog.tenant_id == tenant_id, AuditLog.table_name == "employees")
        )
        actions = {log.action for log in result.scalars().all()}
        assert "EMPLOYEE.CREATE" in actions
        assert "EMPLOYEE.UPDATE" in actions
        assert "EMPLOYEE.DEACTIVATE" in actions
        assert "EMPLOYEE.REACTIVATE" in actions
        assert "EMPLOYEE.SOFT_DELETE" in actions
