from __future__ import annotations

from typing import Any, Tuple

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AppException
from app.models.stripe_event import StripeEvent


def get_stripe_client(settings=None):
    settings = settings or get_settings()
    try:
        import stripe
    except Exception:
        return None
    if not settings.stripe_api_key:
        return None
    stripe.api_key = settings.stripe_api_key
    return stripe


async def verify_and_record_webhook(
    session: AsyncSession, payload: bytes, signature: str | None, settings=None
) -> Tuple[dict | None, bool, str | None]:
    settings = settings or get_settings()
    stripe_client = get_stripe_client(settings)
    if not stripe_client or not settings.stripe_webhook_secret:
        raise AppException(
            "stripe_not_configured",
            "Stripe webhook secret not configured",
            http_status=500,
        )
    try:
        event = stripe_client.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except Exception as exc:
        raise AppException("invalid_webhook_signature", str(exc), http_status=400) from exc

    event_id = event.get("id")
    event_type = event.get("type")
    if event_id:
        existing = await session.execute(select(StripeEvent).where(StripeEvent.event_id == event_id))
        existing_event = existing.scalar_one_or_none()
        if existing_event:
            return None, True, existing_event.event_type
        try:
            session.add(StripeEvent(event_id=event_id, event_type=event_type))
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return None, True, event_type

    return event, False, event_type


__all__ = ["get_stripe_client", "verify_and_record_webhook"]
