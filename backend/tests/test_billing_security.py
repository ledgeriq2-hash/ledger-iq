from __future__ import annotations

import asyncio
import uuid

import pytest
from httpx import AsyncClient
from starlette import status

from app.config import get_settings
from app.database import async_session_maker
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.services import billing_service
from app.core.exceptions import AppException


@pytest.mark.anyio
async def test_billing_webhook_rejects_invalid_signature(client: AsyncClient, monkeypatch):
    settings = get_settings()
    settings.stripe_webhook_secret = "secret"

    class StubWebhook:
        @staticmethod
        def construct_event(payload, signature, secret):  # noqa: ANN001
            raise ValueError("bad signature")

    class StubStripe:
        Webhook = StubWebhook

    monkeypatch.setattr(billing_service, "_get_stripe", lambda _settings=None: StubStripe())

    resp = await client.post(
        "/api/v1/billing/webhook",
        content=b"{}",
        headers={"Stripe-Signature": "bad"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.text
    body = resp.json()
    assert body.get("error", {}).get("code") == "invalid_webhook_signature"


@pytest.mark.anyio
async def test_paid_feature_requires_active_subscription(register_owner):
    registration = await register_owner()
    tenant_id = uuid.UUID(registration["tenant"]["id"])

    async with async_session_maker() as session:
        await billing_service.ensure_default_plans(session)
        subscription = TenantSubscription(
            tenant_id=tenant_id,
            plan_code="pro",
            status="canceled",
            stripe_subscription_id="sub_test",
        )
        session.add(subscription)
        await session.commit()
        await session.refresh(subscription)

        with pytest.raises(AppException) as excinfo:
            await billing_service.enforce_plan_limit(session, tenant_id, "ai_calls")
        assert excinfo.value.code == "subscription_required"
