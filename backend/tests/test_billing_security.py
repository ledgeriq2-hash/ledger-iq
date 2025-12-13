from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from starlette import status

from app.config import get_settings
from app.database import async_session_maker
from app.models.stripe_event import StripeEvent
from app.models.tenant_subscription import TenantSubscription
from app.services import billing_service


def _sign(payload: bytes, secret: str) -> str:
    timestamp = int(time.time())
    signature = hmac.new(secret.encode(), msg=f"{timestamp}.{payload.decode()}".encode(), digestmod=hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


@pytest.mark.anyio
async def test_billing_webhook_rejects_invalid_signature(client: AsyncClient):
    settings = get_settings()
    settings.stripe_api_key = "sk_test_123"
    settings.stripe_webhook_secret = "whsec_test"

    payload = b'{"id":"evt_invalid","type":"customer.subscription.updated","data":{"object":{}}}'
    resp = await client.post(
        "/api/v1/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": "t=1,v1=bogus"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.text
    assert resp.json().get("error", {}).get("code") == "invalid_webhook_signature"


@pytest.mark.anyio
async def test_billing_webhook_idempotent_processing(client: AsyncClient):
    settings = get_settings()
    settings.stripe_api_key = "sk_test_123"
    settings.stripe_webhook_secret = "whsec_test"

    event_id = f"evt_{uuid.uuid4().hex}"
    payload_dict = {
        "id": event_id,
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_test",
                "status": "active",
                "metadata": {"tenant_id": str(uuid.uuid4()), "plan_code": "pro"},
                "current_period_end": int(time.time()),
            }
        },
    }
    payload = json.dumps(payload_dict).encode()
    signature = _sign(payload, settings.stripe_webhook_secret)

    first = await client.post(
        "/api/v1/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": signature},
    )
    assert first.status_code == status.HTTP_200_OK, first.text

    second = await client.post(
        "/api/v1/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": signature},
    )
    assert second.status_code == status.HTTP_200_OK, second.text

    async with async_session_maker() as session:
        result = await session.execute(select(StripeEvent).where(StripeEvent.event_id == event_id))
        events = result.scalars().all()
        assert len(events) == 1


@pytest.mark.anyio
async def test_paid_feature_requires_active_subscription(client: AsyncClient, register_owner):
    registration = await register_owner()
    tenant_id = uuid.UUID(registration["tenant"]["id"])
    token = registration["tokens"]["access_token"]

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

    create = await client.post(
        "/api/v1/users/",
        json={"email": f"user-{uuid.uuid4().hex[:6]}@example.com", "password": "Secret123!", "full_name": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create.status_code in (status.HTTP_402_PAYMENT_REQUIRED, status.HTTP_403_FORBIDDEN)
