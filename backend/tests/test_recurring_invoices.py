from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, UTC
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session_maker
from app.models.invoice import Invoice
from app.services import recurring_invoice_service
from app.tasks.recurring_tasks import run_due_recurring_invoices


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _today():
    return date.today()


@pytest.mark.anyio
async def test_recurring_invoice_run_now(client: AsyncClient, register_owner):
    owner = await register_owner()
    headers = auth_headers(owner["tokens"]["access_token"])

    cust_res = await client.post(
        "/api/v1/customers/",
        json={"code": "RECUR-001", "name": "Recurring Co", "email": "rec@example.com"},
        headers=headers,
    )
    assert cust_res.status_code == 201, cust_res.text
    customer = cust_res.json()

    today = _today()
    payload = {
        "customer_id": customer["id"],
        "frequency": "weekly",
        "interval": 1,
        "template": {
            "customer_id": customer["id"],
            "issue_date": today.isoformat(),
            "due_date": (today + timedelta(days=7)).isoformat(),
            "status": "SENT",
            "currency": "USD",
            "items": [{"description": "Subscription", "quantity": "1", "unit_price": "25.00", "tax_rate": "0"}],
        },
    }

    rec_res = await client.post("/api/v1/recurring-invoices/", json=payload, headers=headers)
    assert rec_res.status_code == 201, rec_res.text
    rec_id = rec_res.json()["id"]
    assert rec_res.json()["next_run_at"]

    run_res = await client.post(f"/api/v1/recurring-invoices/{rec_id}/run", headers=headers)
    assert run_res.status_code == 200, run_res.text
    invoice = run_res.json()
    assert invoice["customer_id"] == customer["id"]

    rec_after = await client.get(f"/api/v1/recurring-invoices/{rec_id}", headers=headers)
    assert rec_after.status_code == 200
    data_after = rec_after.json()
    assert data_after["last_run_at"] is not None
    assert data_after["next_run_at"] is not None


@pytest.mark.anyio
async def test_recurring_invoice_run_now_with_frozen_clock(monkeypatch, client: AsyncClient, register_owner):
    owner = await register_owner()
    headers = auth_headers(owner["tokens"]["access_token"])

    fake_now = datetime(2025, 1, 1, 10, 0, tzinfo=UTC)

    class FrozenDate(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz:
                return fake_now
            return fake_now.replace(tzinfo=None)

    class FrozenDateOnly(date):
        @classmethod
        def today(cls):
            return fake_now.date()

    monkeypatch.setattr(recurring_invoice_service, "datetime", FrozenDate)
    monkeypatch.setattr(recurring_invoice_service, "date", FrozenDateOnly)

    cust_res = await client.post(
        "/api/v1/customers/",
        json={"code": "FROZEN-001", "name": "Frozen Co", "email": "frozen@example.com"},
        headers=headers,
    )
    assert cust_res.status_code == 201, cust_res.text
    customer = cust_res.json()

    payload = {
        "customer_id": customer["id"],
        "frequency": "weekly",
        "interval": 1,
        "next_run_at": fake_now.isoformat(),
        "template": {
            "customer_id": customer["id"],
            "issue_date": fake_now.date().isoformat(),
            "currency": "USD",
            "status": "SENT",
            "items": [{"description": "Frozen", "quantity": "1", "unit_price": "10.00", "tax_rate": "0"}],
        },
    }

    rec_res = await client.post("/api/v1/recurring-invoices/", json=payload, headers=headers)
    assert rec_res.status_code == 201, rec_res.text
    rec_id = rec_res.json()["id"]

    run_res = await client.post(f"/api/v1/recurring-invoices/{rec_id}/run", headers=headers)
    assert run_res.status_code == 200, run_res.text
    invoice = run_res.json()
    assert invoice["customer_id"] == customer["id"]
    assert datetime.fromisoformat(invoice["issue_date"]).date() == fake_now.date()

    rec_after = await client.get(f"/api/v1/recurring-invoices/{rec_id}", headers=headers)
    assert rec_after.status_code == 200
    data_after = rec_after.json()
    assert datetime.fromisoformat(data_after["last_run_at"]) == fake_now.replace(tzinfo=None)
    expected_next = (fake_now + timedelta(days=7)).replace(tzinfo=None)
    assert datetime.fromisoformat(data_after["next_run_at"]) == expected_next


@pytest.mark.anyio
async def test_recurring_invoice_tenant_isolation(client: AsyncClient, register_owner):
    owner1 = await register_owner()
    owner2 = await register_owner()

    cust_res = await client.post(
        "/api/v1/customers/",
        json={"code": "TENANT-ONE", "name": "Tenant One", "email": "one@example.com"},
        headers=auth_headers(owner1["tokens"]["access_token"]),
    )
    assert cust_res.status_code == 201, cust_res.text
    customer = cust_res.json()

    today = _today()
    payload = {
        "customer_id": customer["id"],
        "frequency": "daily",
        "template": {
            "customer_id": customer["id"],
            "issue_date": today.isoformat(),
            "currency": "USD",
            "status": "SENT",
            "items": [{"description": "One", "quantity": "1", "unit_price": "5.00", "tax_rate": "0"}],
        },
    }
    rec_res = await client.post("/api/v1/recurring-invoices/", json=payload, headers=auth_headers(owner1["tokens"]["access_token"]))
    assert rec_res.status_code == 201, rec_res.text
    rec_id = rec_res.json()["id"]

    run_res = await client.post(f"/api/v1/recurring-invoices/{rec_id}/run", headers=auth_headers(owner2["tokens"]["access_token"]))
    assert run_res.status_code == 404


@pytest.mark.anyio
async def test_process_due_recurring_invoices_handles_monthly_rollover(client: AsyncClient, register_owner):
    owner = await register_owner()
    tenant_id = UUID(owner["tenant"]["id"])
    headers = auth_headers(owner["tokens"]["access_token"])

    cust_res = await client.post(
        "/api/v1/customers/",
        json={"code": "MONTHLY-001", "name": "Monthly Co", "email": "monthly@example.com"},
        headers=headers,
    )
    assert cust_res.status_code == 201, cust_res.text
    customer = cust_res.json()

    base_today = _today()
    today = base_today.replace(day=min(base_today.day, 28))
    template = {
        "customer_id": customer["id"],
        "issue_date": today.isoformat(),
        "due_date": (today + timedelta(days=5)).isoformat(),
        "status": "SENT",
        "currency": "USD",
        "items": [{"description": "Monthly", "quantity": "1", "unit_price": "15.00", "tax_rate": "0"}],
    }

    async with async_session_maker() as session:
        rec = await recurring_invoice_service.create_recurring_invoice(
            session,
            tenant_id,
            {
                "customer_id": customer["id"],
                "frequency": "monthly",
                "interval": 1,
                "day_of_month": 31,
                "next_run_at": datetime.now(UTC) - timedelta(days=1),
                "template": template,
            },
        )
        generated = await recurring_invoice_service.process_due_recurring_invoices(session, tenant_id=tenant_id)
        assert len(generated) == 1
        refreshed = await recurring_invoice_service.get_recurring_invoice(session, tenant_id, rec.id)
        assert refreshed.last_run_at is not None
        assert refreshed.next_run_at.day <= 31

        # verify invoice exists
        inv_result = await session.execute(
            select(Invoice).where(Invoice.tenant_id == tenant_id, Invoice.customer_id == UUID(customer["id"]))
        )
        assert inv_result.scalars().first() is not None


@pytest.mark.anyio
async def test_celery_task_runs_due(client: AsyncClient, register_owner):
    owner = await register_owner()
    tenant_id = UUID(owner["tenant"]["id"])
    headers = auth_headers(owner["tokens"]["access_token"])

    cust_res = await client.post(
        "/api/v1/customers/",
        json={"code": "TASK-001", "name": "Task Co", "email": "task@example.com"},
        headers=headers,
    )
    assert cust_res.status_code == 201, cust_res.text
    customer = cust_res.json()

    today = _today()
    template = {
        "customer_id": customer["id"],
        "issue_date": today.isoformat(),
        "currency": "USD",
        "status": "SENT",
        "items": [{"description": "Task", "quantity": "1", "unit_price": "3.00", "tax_rate": "0"}],
    }

    async with async_session_maker() as session:
        await recurring_invoice_service.create_recurring_invoice(
            session,
            tenant_id,
            {
                "customer_id": customer["id"],
                "frequency": "daily",
                "interval": 1,
                "next_run_at": datetime.now(UTC) - timedelta(minutes=5),
                "template": template,
            },
        )

    result = await asyncio.to_thread(run_due_recurring_invoices)
    assert result["generated"] >= 1
