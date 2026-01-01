from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session_maker
from app.models.billing_plan import BillingPlan
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.services import billing_service, stripe_service


class StubStripe:
    api_key = None

    def __init__(self):
        self.created_customers: list[dict] = []
        self.checkout_sessions: list[dict] = []
        self.portal_sessions: list[dict] = []

        class _Customer:
            @staticmethod
            def create(name, metadata=None):
                cid = f"cus_{len(self.created_customers)+1}"
                self.created_customers.append({"id": cid, "name": name, "metadata": metadata})
                return type("Obj", (), {"id": cid})

        class _CheckoutSession:
            @staticmethod
            def create(**kwargs):
                sid = f"cs_{len(self.checkout_sessions)+1}"
                url = f"https://checkout.test/{sid}"
                self.checkout_sessions.append({"id": sid, "url": url, **kwargs})
                return type("Obj", (), {"id": sid, "url": url, "subscription": "sub_test"})

        class _BillingPortalSession:
            @staticmethod
            def create(**kwargs):
                url = f"https://portal.test/{len(self.portal_sessions)+1}"
                self.portal_sessions.append({"url": url, **kwargs})
                return type("Obj", (), {"url": url})

        class _Webhook:
            @staticmethod
            def construct_event(payload, signature, secret):
                if signature != "sig_valid":
                    raise ValueError("invalid signature")
                return json.loads(payload)

        self.Customer = _Customer
        self.checkout = type("Checkout", (), {"Session": _CheckoutSession})
        self.billing_portal = type("BillingPortal", (), {"Session": _BillingPortalSession})
        self.Webhook = _Webhook


async def _seed_plan(session, code=None, price_id="price_123"):
    code = code or f"pro_{uuid4().hex[:6]}"
    plan = BillingPlan(
        code=code,
        name="Pro",
        price_cents=4900,
        currency="usd",
        interval="month",
        metadata_json={"stripe_price_id": price_id},
        limits_json={"users": 5},
    )
    session.add(plan)
    await session.commit()
    await session.refresh(plan)
    return plan


async def _seed_tenant(session):
    tenant = Tenant(name="TestCo", slug=f"tenant-{uuid4().hex[:6]}")
    session.add(tenant)
    await session.commit()
    await session.refresh(tenant)
    return tenant


@pytest.mark.asyncio
async def test_checkout_session_uses_stripe_and_reuses_customer(monkeypatch):
    stripe = StubStripe()
    monkeypatch.setattr(stripe_service, "get_stripe_client", lambda _settings=None: stripe)
    monkeypatch.setattr(billing_service, "_get_stripe", lambda _settings=None: stripe)
    settings = get_settings()
    settings.stripe_api_key = "sk_test"

    async with async_session_maker() as session:
        plan = await _seed_plan(session)
        tenant = await _seed_tenant(session)

        await billing_service.create_checkout_session(
            session=session,
            tenant_id=tenant.id,
            plan_code=plan.code,
            success_url="https://app.test/success",
            cancel_url="https://app.test/cancel",
            settings=settings,
        )
        subscription = (
            await session.execute(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant.id))
        ).scalar_one()
        first_customer_id = subscription.stripe_customer_id
        assert first_customer_id is not None
        assert subscription.status == "pending"

        # second checkout reuses customer
        checkout2 = await billing_service.create_checkout_session(
            session=session,
            tenant_id=tenant.id,
            plan_code=plan.code,
            success_url="https://app.test/success",
            cancel_url="https://app.test/cancel",
            settings=settings,
        )
        assert checkout2["url"] != ""
        subscription = (
            await session.execute(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant.id))
        ).scalar_one()
        assert subscription.stripe_customer_id == first_customer_id
        assert len(stripe.created_customers) == 1


@pytest.mark.asyncio
async def test_webhook_signature_and_idempotency(monkeypatch):
    stripe = StubStripe()
    monkeypatch.setattr(stripe_service, "get_stripe_client", lambda _settings=None: stripe)
    monkeypatch.setattr(billing_service, "_get_stripe", lambda _settings=None: stripe)
    settings = get_settings()
    settings.stripe_webhook_secret = "secret"
    settings.stripe_api_key = "sk_test"

    async with async_session_maker() as session:
        plan = await _seed_plan(session)
        tenant = await _seed_tenant(session)
        sub = await billing_service._get_or_create_subscription(session, tenant.id, settings=settings)
        sub.plan_code = plan.code
        await session.commit()

        payload = {
            "id": "evt_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {"tenant_id": str(tenant.id), "plan_code": plan.code},
                    "subscription": "sub_123",
                    "customer": "cus_123",
                    "id": "cs_test_123",
                }
            },
        }
        resp = await billing_service.handle_webhook_event(
            session, json.dumps(payload).encode(), signature="sig_valid", settings=settings
        )
        assert resp["event_type"] == "checkout.session.completed"
        subscription = (
            await session.execute(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant.id))
        ).scalar_one()
        assert subscription.status == "active"
        assert subscription.stripe_subscription_id == "sub_123"

        # Duplicate event should be idempotent
        resp_dup = await billing_service.handle_webhook_event(
            session, json.dumps(payload).encode(), signature="sig_valid", settings=settings
        )
        assert resp_dup.get("idempotent") is True
        subscription_after = (
            await session.execute(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant.id))
        ).scalar_one()
        assert subscription_after.status == "active"


@pytest.mark.asyncio
async def test_webhook_subscription_status_changes(monkeypatch):
    stripe = StubStripe()
    monkeypatch.setattr(stripe_service, "get_stripe_client", lambda _settings=None: stripe)
    monkeypatch.setattr(billing_service, "_get_stripe", lambda _settings=None: stripe)
    settings = get_settings()
    settings.stripe_webhook_secret = "secret"
    settings.stripe_api_key = "sk_test"

    async with async_session_maker() as session:
        plan = await _seed_plan(session)
        tenant = await _seed_tenant(session)
        sub = await billing_service._get_or_create_subscription(session, tenant.id, settings=settings)
        sub.plan_code = plan.code
        await session.commit()

        updated_payload = {
            "id": "evt_2",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_456",
                    "status": "past_due",
                    "metadata": {"tenant_id": str(tenant.id), "plan_code": plan.code},
                }
            },
        }
        await billing_service.handle_webhook_event(
            session, json.dumps(updated_payload).encode(), signature="sig_valid", settings=settings
        )
        subscription = (
            await session.execute(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant.id))
        ).scalar_one()
        assert subscription.status == "past_due"

        deleted_payload = {
            "id": "evt_3",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_456",
                    "metadata": {"tenant_id": str(tenant.id), "plan_code": plan.code},
                }
            },
        }
        await billing_service.handle_webhook_event(
            session, json.dumps(deleted_payload).encode(), signature="sig_valid", settings=settings
        )
        subscription = (
            await session.execute(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant.id))
        ).scalar_one()
        assert subscription.status == "canceled"


@pytest.mark.asyncio
async def test_portal_session_requires_customer(monkeypatch):
    stripe = StubStripe()
    monkeypatch.setattr(stripe_service, "get_stripe_client", lambda _settings=None: stripe)
    monkeypatch.setattr(billing_service, "_get_stripe", lambda _settings=None: stripe)
    settings = get_settings()
    settings.stripe_api_key = "sk_test"

    async with async_session_maker() as session:
        plan = await _seed_plan(session)
        tenant = await _seed_tenant(session)
        sub = await billing_service._get_or_create_subscription(session, tenant.id, settings=settings)
        sub.plan_code = plan.code
        sub.stripe_customer_id = "cus_123"
        await session.commit()

        portal = await billing_service.create_customer_portal_session(
            session, tenant.id, return_url="https://app.test/billing", settings=settings
        )
        assert portal["url"].startswith("https://portal.test/")


@pytest.mark.asyncio
async def test_enforce_plan_limit_requires_active_subscription(monkeypatch):
    stripe = StubStripe()
    monkeypatch.setattr(stripe_service, "get_stripe_client", lambda _settings=None: stripe)
    monkeypatch.setattr(billing_service, "_get_stripe", lambda _settings=None: stripe)
    settings = get_settings()
    settings.stripe_api_key = "sk_test"

    async with async_session_maker() as session:
        plan = await _seed_plan(session)
        tenant = await _seed_tenant(session)
        sub = await billing_service._get_or_create_subscription(session, tenant.id, settings=settings)
        sub.plan_code = plan.code
        sub.status = "inactive"
        await session.commit()

        with pytest.raises(billing_service.AppException):
            await billing_service.enforce_plan_limit(session, tenant.id, "users")

        sub.status = "active"
        await session.commit()
        await billing_service.enforce_plan_limit(session, tenant.id, "users")
