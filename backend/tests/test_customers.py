from __future__ import annotations

from datetime import date
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.database import async_session_maker
from app.initial_data import seed_tenant
from app.models.invoice import InvoiceStatus
from app.models.journal_entry import JournalEntry
from app.models.journal_entry_line import JournalEntryLine
from app.models.tenant import Tenant


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


async def _create_customer(client: AsyncClient, token: str, name: str = "ACME") -> dict:
    payload = {
        "name": name,
        "email": f"{name.lower()}@example.com",
        "phone": "123",
        "address": "123 Main St",
    }
    response = await client.post("/api/v1/customers/", json=payload, headers=_auth_headers(token))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.anyio
async def test_create_customer(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    customer = await _create_customer(client, token)
    assert customer["name"] == "ACME"
    assert customer["email"] == "acme@example.com"


@pytest.mark.anyio
async def test_update_customer(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]

    customer = await _create_customer(client, token)
    update_payload = {"name": "Updated Co", "email": "updated@example.com"}
    response = await client.put(
        f"/api/v1/customers/{customer['id']}",
        json=update_payload,
        headers=_auth_headers(token),
    )
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["name"] == "Updated Co"
    assert updated["email"] == "updated@example.com"


@pytest.mark.anyio
async def test_tenant_cannot_access_another_tenants_customer(client: AsyncClient, register_owner):
    auth_a = await register_owner()
    token_a = auth_a["tokens"]["access_token"]
    customer_a = await _create_customer(client, token_a, name="TenantA")

    auth_b = await register_owner()
    token_b = auth_b["tokens"]["access_token"]

    get_response = await client.get(
        f"/api/v1/customers/{customer_a['id']}",
        headers=_auth_headers(token_b),
    )
    assert get_response.status_code == 404

    update_response = await client.put(
        f"/api/v1/customers/{customer_a['id']}",
        json={"name": "Hacker"},
        headers=_auth_headers(token_b),
    )
    assert update_response.status_code == 404


@pytest.mark.anyio
async def test_paid_invoice_posts_journal_entries(client: AsyncClient, register_owner):
    auth = await register_owner()
    token = auth["tokens"]["access_token"]
    tenant_id = uuid.UUID(auth["tenant"]["id"])

    # Seed chart of accounts and mappings for this tenant so journal posting can occur.
    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_id)
        await seed_tenant(session, tenant)

    customer = await _create_customer(client, token, name="InvoiceCustomer")
    invoice_payload = {
        "customer_id": customer["id"],
        "issue_date": date.today().isoformat(),
        "due_date": date.today().isoformat(),
        "status": InvoiceStatus.PAID.value,
        "currency": "USD",
        "items": [
            {"description": "Services", "quantity": "1", "unit_price": "100.00", "tax_rate": "0", "line_total": "100.00"}
        ],
    }
    response = await client.post("/api/v1/invoices/", json=invoice_payload, headers=_auth_headers(token))
    assert response.status_code == 201, response.text
    invoice_data = response.json()

    async with async_session_maker() as session:
        entries_result = await session.execute(
            select(JournalEntry).where(JournalEntry.reference == str(invoice_data["id"]))
        )
        entries = entries_result.scalars().all()
        assert entries, "Expected journal entry for paid invoice"

        lines_result = await session.execute(
            select(JournalEntryLine).where(JournalEntryLine.journal_entry_id == entries[0].id)
        )
        lines = lines_result.scalars().all()
        assert len(lines) == 2

        debits = sum(float(line.debit) for line in lines)
        credits = sum(float(line.credit) for line in lines)
        assert round(debits, 2) == round(credits, 2) == round(float(invoice_data["total_amount"]), 2)
