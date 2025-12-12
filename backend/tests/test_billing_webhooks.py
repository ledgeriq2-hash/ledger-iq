from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.services import billing_service


class StubSubscription:
    def __init__(self, tenant_id):
        self.tenant_id = tenant_id
        self.plan_code: str | None = None
        self.status: str | None = None
        self.stripe_customer_id: str | None = None
        self.stripe_subscription_id: str | None = None
        self.checkout_session_id: str | None = None
        self.current_period_end = None
        self.cancel_at_period_end: bool | None = None


class StubSession:
    def __init__(self, subscription: StubSubscription | None = None):
        self.subscription = subscription
        self.commits = 0
        self.executed_queries = []

    async def execute(self, query):
        self.executed_queries.append(query)

        class _Result:
            def __init__(self, subscription):
                self.subscription = subscription

            def scalar_one_or_none(self):
                return self.subscription

        return _Result(self.subscription)

    async def commit(self):
        self.commits += 1

    async def refresh(self, _obj):
        return None

    async def add(self, _obj):
        return None


@pytest.mark.asyncio
async def test_create_checkout_session_stubbed(monkeypatch):
    tenant_id = uuid4()
    subscription = StubSubscription(tenant_id)
    session = StubSession(subscription)

    class StubPlan:
        def __init__(self):
            self.code = "pro"
            self.metadata_json = {"stripe_price_id": None}

    async def fake_get_plan(_session, code):
        assert code == "pro"
        return StubPlan()

    async def fake_get_or_create(_session, _tenant_id):
        return subscription

    async def fake_sync(*_args, **_kwargs):
        return None

    monkeypatch.setattr(billing_service, "_get_stripe", lambda _settings: None)
    monkeypatch.setattr(billing_service, "get_plan", fake_get_plan)
    monkeypatch.setattr(billing_service, "_get_or_create_subscription", fake_get_or_create)
    monkeypatch.setattr(billing_service, "_sync_tenant_plan", fake_sync)

    result = await billing_service.create_checkout_session(
        session=session,
        tenant_id=tenant_id,
        plan_code="pro",
        success_url="http://success",
        cancel_url="http://cancel",
    )

    assert result["url"].endswith("plan=pro")
    assert subscription.plan_code == "pro"
    assert subscription.status == "pending"


@pytest.mark.asyncio
async def test_webhook_checkout_completed(monkeypatch):
    tenant_id = uuid4()
    subscription = StubSubscription(tenant_id)
    session = StubSession(subscription)

    async def fake_get_or_create(_session, _tenant_id):
        return subscription

    async def fake_sync(*_args, **_kwargs):
        return None

    monkeypatch.setattr(billing_service, "_get_stripe", lambda _settings: None)
    monkeypatch.setattr(billing_service, "_get_or_create_subscription", fake_get_or_create)
    monkeypatch.setattr(billing_service, "_sync_tenant_plan", fake_sync)

    payload = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"tenant_id": str(tenant_id), "plan_code": "pro"},
                "subscription": "sub_123",
                "customer": "cus_123",
                "id": "cs_test_123",
            }
        },
    }

    resp = await billing_service.handle_webhook_event(session, json.dumps(payload).encode(), signature=None)
    assert resp["event_type"] == "checkout.session.completed"
    assert subscription.status == "active"
    assert subscription.plan_code == "pro"
    assert subscription.stripe_subscription_id == "sub_123"
    assert subscription.checkout_session_id == "cs_test_123"


@pytest.mark.asyncio
async def test_webhook_subscription_update(monkeypatch):
    tenant_id = uuid4()
    subscription = StubSubscription(tenant_id)
    session = StubSession(subscription)

    async def fake_get_or_create(_session, _tenant_id):
        return subscription

    async def fake_sync(*_args, **_kwargs):
        return None

    monkeypatch.setattr(billing_service, "_get_stripe", lambda _settings: None)
    monkeypatch.setattr(billing_service, "_get_or_create_subscription", fake_get_or_create)
    monkeypatch.setattr(billing_service, "_sync_tenant_plan", fake_sync)

    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    payload = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_456",
                "status": "past_due",
                "current_period_end": now_ts,
                "cancel_at_period_end": True,
                "metadata": {"tenant_id": str(tenant_id), "plan_code": "pro"},
            }
        },
    }

    resp = await billing_service.handle_webhook_event(session, json.dumps(payload).encode(), signature=None)
    assert resp["event_type"] == "customer.subscription.updated"
    assert subscription.status == "past_due"
    assert subscription.plan_code == "pro"
    assert subscription.stripe_subscription_id == "sub_456"
    assert subscription.cancel_at_period_end is True
    assert subscription.current_period_end is not None
