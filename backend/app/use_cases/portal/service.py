from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.accounting.use_cases.generate_client_statement import generate_client_statement
from app.core.exceptions import AppException
from app.core.pagination import PaginationParams, paginate_query
from app.core.rate_limit import enforce_rate_limit
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.models.portal_token import PortalEntityType
from app.schemas.customer import CustomerPublic
from app.schemas.invoice import InvoicePublic
from app.schemas.payment import PaymentPublic
from app.schemas.portal import (
    PortalActivityItem,
    PortalBalanceResponse,
    PortalInvoicesResponse,
    PortalLinkRequest,
    PortalPaymentsResponse,
    PortalStatementResponse,
    PortalSummaryResponse,
    PortalSummaryStats,
)
from app.services import (
    customer_service,
    email_service,
    portal_service,
)

logger = logging.getLogger(__name__)


def token_expiry(expires_in: int | None, default_seconds: int = 86400) -> datetime:
    seconds = expires_in if expires_in and expires_in > 0 else default_seconds
    return datetime.now(UTC) + timedelta(seconds=seconds)


async def portal_rate_limit(request: Request, settings: Any, key: str = "portal_view") -> None:
    await enforce_rate_limit(request, key, settings.portal_rate_limit_per_minute)


async def _ensure_customer_exists(session: AsyncSession, tenant_id: UUID, customer_id: UUID) -> CustomerPublic:
    customer = await customer_service.get_customer(session, tenant_id, customer_id)
    if not customer:
        raise AppException(
            code="customer_not_found",
            message="Customer not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )
    return CustomerPublic.model_validate(customer)


def invoice_activity_item(invoice: InvoicePublic) -> PortalActivityItem:
    return PortalActivityItem(
        id=invoice.id,
        title=f"Invoice {invoice.id}",
        description=f"{invoice.status} ? {invoice.total_amount} {invoice.currency}",
        timestamp=invoice.created_at.isoformat(),
    )


def payment_activity_item(payment: PaymentPublic) -> PortalActivityItem:
    timestamp = (payment.paid_at or payment.created_at).isoformat()
    return PortalActivityItem(
        id=payment.id,
        title=f"Payment {payment.reference or payment.id}",
        description=f"{payment.amount} via {payment.method}",
        timestamp=timestamp,
    )


def build_recent_activity(items: list[PortalActivityItem], limit: int = 5) -> list[PortalActivityItem]:
    sorted_items = sorted(items, key=lambda item: item.timestamp or "", reverse=True)
    return sorted_items[:limit]


async def validate_portal_token_or_error(
    session: AsyncSession,
    token: str,
    expected_type: PortalEntityType | None = None,
):
    validation = await portal_service.validate_portal_token(session, token)
    if not validation:
        raise AppException(
            code="portal_token_invalid",
            message="Invalid or expired portal token",
            http_status=status.HTTP_404_NOT_FOUND,
        )
    entity_type, entity, portal_token = validation
    if expected_type and entity_type != expected_type:
        raise AppException(
            code="portal_token_forbidden",
            message="Portal token is not valid for this portal type",
            http_status=status.HTTP_403_FORBIDDEN,
        )
    if not entity:
        raise AppException(
            code="portal_entity_not_found",
            message="Portal entity not found",
            http_status=status.HTTP_404_NOT_FOUND,
        )
    return entity_type, entity, portal_token


async def get_customer_and_invoices(
    session: AsyncSession, tenant_id: UUID, customer_id: UUID
) -> tuple[CustomerPublic, list[InvoicePublic]]:
    customer, invoices = await customer_service.get_customer_with_open_invoices(session, tenant_id, customer_id)
    if not customer:
        raise AppException(
            code="customer_not_found", message="Customer not found", http_status=status.HTTP_404_NOT_FOUND
        )
    invoice_models = [InvoicePublic.model_validate(inv) for inv in invoices]
    return CustomerPublic.model_validate(customer), invoice_models


async def get_customer_payments(
    session: AsyncSession, tenant_id: UUID, customer_id: UUID
) -> list[PaymentPublic]:
    result = await session.execute(
        select(Payment).where(Payment.tenant_id == tenant_id, Payment.customer_id == customer_id).order_by(Payment.created_at.desc()).limit(25)
    )
    payments = result.scalars().all()
    return [PaymentPublic.model_validate(payment) for payment in payments]


async def generate_portal_link_use_case(
    payload: PortalLinkRequest,
    request: Request,
    session: AsyncSession,
    tenant_id: UUID,
    settings: Any,
) -> dict[str, Any]:
    await portal_rate_limit(request, settings, key="portal")
    if not payload.client_id:
        raise AppException(
            code="customer_required", message="customer_id is required", http_status=status.HTTP_400_BAD_REQUEST
        )
    customer = await _ensure_customer_exists(session, tenant_id, payload.client_id)

    expires_at = token_expiry(payload.expires_in)
    raw_token, token = await portal_service.create_portal_token_for_customer(
        session, tenant_id, payload.client_id, expires_at
    )
    relative_url = f"/portal/{raw_token}"
    portal_url = email_service.build_frontend_url(relative_url, settings=settings) or relative_url

    return {"success": True, "url": portal_url, "expires_at": token.expires_at, "token_id": token.id}


async def portal_summary_response(session: AsyncSession, portal_token, settings: Any) -> PortalSummaryResponse:
    customer_model, invoices = await get_customer_and_invoices(session, portal_token.tenant_id, portal_token.entity_id)
    payment_models = await get_customer_payments(session, portal_token.tenant_id, portal_token.entity_id)
    recent_candidates: list[PortalActivityItem] = [
        invoice_activity_item(inv) for inv in invoices
    ] + [payment_activity_item(payment) for payment in payment_models]
    recent_activity = build_recent_activity(recent_candidates)
    total_open_amount = sum((inv.total_amount for inv in invoices), start=0)
    stats = PortalSummaryStats(open_invoices=len(invoices), total_open_amount=total_open_amount)
    return PortalSummaryResponse(client=customer_model, recent_activity=recent_activity, stats=stats)


async def portal_invoices_response(
    session: AsyncSession, portal_token, params: PaginationParams
) -> PortalInvoicesResponse:
    await _ensure_customer_exists(session, portal_token.tenant_id, portal_token.entity_id)
    statement = select(Invoice).where(
        Invoice.tenant_id == portal_token.tenant_id,
        Invoice.customer_id == portal_token.entity_id,
        Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
    )
    invoices, total = await paginate_query(session, statement, params)
    invoice_models = [InvoicePublic.model_validate(inv) for inv in invoices]
    return PortalInvoicesResponse.from_results(items=invoice_models, total=total, params=params)


async def portal_payments_response(
    session: AsyncSession, portal_token, params: PaginationParams
) -> PortalPaymentsResponse:
    await _ensure_customer_exists(session, portal_token.tenant_id, portal_token.entity_id)
    statement = select(Payment).where(
        Payment.tenant_id == portal_token.tenant_id,
        Payment.customer_id == portal_token.entity_id,
    )
    payments, total = await paginate_query(session, statement, params)
    payment_models = [PaymentPublic.model_validate(payment) for payment in payments]
    return PortalPaymentsResponse.from_results(items=payment_models, total=total, params=params)


async def portal_statement_response(
    session: AsyncSession,
    portal_token,
    *,
    from_date: date | None,
    to_date: date | None,
) -> PortalStatementResponse:
    statement = await generate_client_statement(
        session,
        tenant_id=portal_token.tenant_id,
        client_id=portal_token.entity_id,
        from_date=from_date,
        to_date=to_date,
    )
    return PortalStatementResponse(statement=statement)


async def portal_balance_response(
    session: AsyncSession,
    portal_token,
    *,
    as_of_date: date | None,
) -> PortalBalanceResponse:
    statement = await generate_client_statement(
        session,
        tenant_id=portal_token.tenant_id,
        client_id=portal_token.entity_id,
        from_date=None,
        to_date=as_of_date,
    )
    return PortalBalanceResponse(
        client_id=portal_token.entity_id,
        as_of_date=as_of_date or date.today(),
        balance=statement.get("closing_balance") or 0,
    )


__all__ = [
    "portal_rate_limit",
    "validate_portal_token_or_error",
    "generate_portal_link_use_case",
    "portal_summary_response",
    "portal_balance_response",
    "portal_invoices_response",
    "portal_payments_response",
    "portal_statement_response",
]
