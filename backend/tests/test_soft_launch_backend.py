import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.core.soft_launch import is_soft_launch_tenant
from app.database import async_session_maker
from app.initial_data import seed_tenant
from app.main import app
from app.models.error_event import ErrorEvent
from app.models.tenant import Tenant
from app.services import (
    customer_service,
    invoice_service,
    payment_service,
    product_service,
    tenant_service,
    usage_service,
)


# Test-only route to force a 500 for error event capture.
if not any(r.path == "/api/test-error" for r in app.router.routes):
    @app.get("/api/test-error")
    async def _raise_test_error():
        raise RuntimeError("boom")


@pytest.mark.anyio
async def test_soft_launch_helper(monkeypatch):
    settings = get_settings()
    settings.soft_launch_enabled = True
    settings.soft_launch_tenant_slugs = ["pilot-1", "pilot-2"]

    assert is_soft_launch_tenant("pilot-1") is True
    assert is_soft_launch_tenant("pilot-2") is True
    assert is_soft_launch_tenant("other") is False

    settings.soft_launch_enabled = False
    assert is_soft_launch_tenant("pilot-1") is False


@pytest.mark.anyio
async def test_usage_counters_increment(register_owner):
    registration = await register_owner(slug="usage-tenant")
    tenant_id = uuid.UUID(registration["tenant"]["id"])

    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_id)
        await seed_tenant(session, tenant)
        # Record a login and create baseline entities.
        await usage_service.record_login(session, tenant_id)
        await tenant_service.get_tenant(session, tenant_id, scope_id=None)
        product = await product_service.create_product(
            session,
            tenant_id,
            {"name": "Service A", "sku": "SRV-1", "unit_price": "10.00", "is_service": True},
        )
        customer = await customer_service.create_customer(
            session,
            tenant_id,
            {"code": "USAGE-ACME", "name": "Acme", "email": "acme@example.com"},
        )
        invoice = await invoice_service.create_invoice(
            session,
            tenant_id,
            {
                "customer_id": customer.id,
                "issue_date": date.today().isoformat(),
                "due_date": date.today().isoformat(),
                "status": "SENT",
                "currency": "USD",
                "items": [
                    {
                        "product_id": product.id,
                        "description": "Work",
                        "quantity": "1",
                        "unit_price": "10.00",
                        "tax_rate": "0",
                    }
                ],
            },
        )
        invoice_id = invoice.id
        customer_id = customer.id

    async with async_session_maker() as session:
        await payment_service.create_payment(
            session,
            tenant_id,
            {
                "invoice_id": invoice_id,
                "customer_id": customer_id,
                "amount": "10.00",
                "method": "card",
            },
        )

        usage_rows = await usage_service.fetch_recent_usage(session, tenant_id, days=1)

    assert usage_rows, "usage rows should be recorded"
    usage = usage_rows[0]
    assert usage.customers_created == 1
    assert usage.invoices_created == 1
    assert usage.payments_created == 1
    assert usage.total_logins >= 1


@pytest.mark.anyio
async def test_error_event_persisted(client):
    tenant_id = uuid.uuid4()
    response = await client.get("/api/test-error", headers={"X-Tenant-ID": str(tenant_id)})
    assert response.status_code == 500

    async with async_session_maker() as session:
        result = await session.execute(select(ErrorEvent).where(ErrorEvent.tenant_id == tenant_id))
        events = result.scalars().all()
        assert events, "an error event should be stored"
        event = events[0]
        assert event.status_code == 500
        assert event.path == "/api/test-error"


@pytest.mark.anyio
async def test_feedback_flow(client, register_owner):
    registration = await register_owner(slug="feedback-tenant")
    tenant_id = registration["tenant"]["id"]
    access = registration["tokens"]["access_token"]

    # Submit feedback
    response = await client.post(
        "/api/v1/feedback/",
        json={"category": "bug", "message": "Something is wrong"},
        headers={"Authorization": f"Bearer {access}", "X-Tenant-ID": tenant_id},
    )
    assert response.status_code == 201, response.text
    feedback_id = response.json()["id"]

    # Admin fetch
    response_admin = await client.get(
        "/api/v1/admin/feedback",
        headers={"Authorization": f"Bearer {access}", "X-Tenant-ID": tenant_id},
    )
    assert response_admin.status_code == 200, response_admin.text
    items = response_admin.json().get("items", [])
    assert any(item["id"] == feedback_id for item in items)
