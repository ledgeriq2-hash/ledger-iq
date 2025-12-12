from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.rate_limit import enforce_rate_limit
from app.models.portal_token import PortalEntityType
from app.models.user import User
from app.schemas.common import BaseSchema
from app.schemas.customer import CustomerPublic
from app.schemas.invoice import InvoicePublic
from app.schemas.payment import PaymentPublic
from app.schemas.portal import (
    CustomerPortalResponse,
    CustomerInvoicesResponse,
    CustomerPaymentsResponse,
    PortalActivityItem,
    PortalOrder,
    PortalSettings,
    PortalSettingsUpdate,
    PortalSupplierPayment,
    SupplierOrdersResponse,
    SupplierPaymentsResponse,
    SupplierPortalResponse,
)
from app.schemas.supplier import SupplierPublic
from app.services import (
    customer_service,
    email_service,
    payment_service,
    portal_service,
    supplier_service,
    tenant_service,
)


router = APIRouter(prefix="/portal")
logger = logging.getLogger(__name__)


class PortalTokenRequest(BaseSchema):
    customer_id: UUID | None = None
    supplier_id: UUID | None = None
    expires_in: int | None = None  # seconds


class PortalTokenResponse(BaseSchema):
    success: bool = True
    message: str | None = None
    url: str | None = None
    expires_at: datetime | None = None
    token_id: UUID | None = None
    # In production, the URL is not returned; it is emailed instead.


def _token_expiry(expires_in: int | None, default_seconds: int = 86400) -> datetime:
    seconds = expires_in if expires_in and expires_in > 0 else default_seconds
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def _entity_settings_key(entity_type: PortalEntityType) -> str:
    return "customer_settings" if entity_type == PortalEntityType.CUSTOMER else "supplier_settings"


async def _portal_rate_limit(request: Request, settings: Any, key: str = "portal_view") -> None:
    await enforce_rate_limit(request, key, settings.portal_rate_limit_per_minute)


async def _load_portal_settings(session: AsyncSession, tenant_id: UUID, entity_type: PortalEntityType) -> PortalSettings:
    tenant = await tenant_service.get_tenant(session, tenant_id, scope_id=None)
    if not tenant:
        raise AppException(code="tenant_not_found", message="Tenant not found", http_status=status.HTTP_404_NOT_FOUND)
    settings_json = tenant.settings_json if isinstance(tenant.settings_json, dict) else {}
    portal_section = settings_json.get("portal")
    portal_dict = portal_section if isinstance(portal_section, dict) else {}
    entity_settings = portal_dict.get(_entity_settings_key(entity_type))
    entity_dict = entity_settings if isinstance(entity_settings, dict) else {}
    return PortalSettings(
        notifications=bool(entity_dict.get("notifications", True)),
        language=str(entity_dict.get("language") or "en"),
    )


async def _persist_portal_settings(
    session: AsyncSession,
    tenant_id: UUID,
    entity_type: PortalEntityType,
    payload: PortalSettingsUpdate,
) -> PortalSettings | None:
    tenant = await tenant_service.get_tenant(session, tenant_id, scope_id=None)
    if not tenant:
        return None
    settings_json = tenant.settings_json if isinstance(tenant.settings_json, dict) else {}
    portal_section = settings_json.get("portal")
    portal_dict = dict(portal_section) if isinstance(portal_section, dict) else {}
    entity_key = _entity_settings_key(entity_type)
    entity_settings = portal_dict.get(entity_key)
    entity_dict = dict(entity_settings) if isinstance(entity_settings, dict) else {}
    updates = payload.model_dump(exclude_none=True)
    if updates:
        entity_dict.update(updates)
        portal_dict[entity_key] = entity_dict
        new_settings = dict(settings_json)
        new_settings["portal"] = portal_dict
        updated = await tenant_service.update_tenant(session, tenant_id, {"settings_json": new_settings})
        if not updated:
            raise AppException(
                code="portal_settings_save_failed",
                message="Failed to save portal settings",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    notifications = entity_dict.get("notifications", True)
    language = entity_dict.get("language") or "en"
    return PortalSettings(notifications=bool(notifications), language=str(language))


def _invoice_activity_item(invoice: InvoicePublic) -> PortalActivityItem:
    return PortalActivityItem(
        id=invoice.id,
        title=f"Invoice {invoice.id}",
        description=f"{invoice.status} • {invoice.total_amount} {invoice.currency}",
        timestamp=invoice.created_at.isoformat(),
    )


def _payment_activity_item(payment: PaymentPublic) -> PortalActivityItem:
    timestamp = (payment.paid_at or payment.created_at).isoformat()
    return PortalActivityItem(
        id=payment.id,
        title=f"Payment {payment.reference or payment.id}",
        description=f"{payment.amount} via {payment.method}",
        timestamp=timestamp,
    )


def _order_activity_item(order: PortalOrder) -> PortalActivityItem:
    timestamp = order.order_date.isoformat() if order.order_date else str(order.id)
    return PortalActivityItem(
        id=order.id,
        title=order.reference or f"Order {order.id}",
        description=f"{order.total_amount} {order.currency}",
        timestamp=timestamp,
    )


def _supplier_payment_activity_item(payment: PortalSupplierPayment) -> PortalActivityItem:
    timestamp = payment.paid_at or str(payment.id)
    return PortalActivityItem(
        id=payment.id,
        title=payment.reference or f"Payment {payment.id}",
        description=f"{payment.amount} {payment.currency}",
        timestamp=timestamp,
    )


def _build_recent_activity(items: list[PortalActivityItem], limit: int = 5) -> list[PortalActivityItem]:
    sorted_items = sorted(items, key=lambda item: item.timestamp or "", reverse=True)
    return sorted_items[:limit]


def _expense_to_order(expense: Any) -> PortalOrder:
    reference = expense.description or str(expense.id)
    return PortalOrder(
        id=expense.id,
        reference=reference,
        status="RECORDED",
        total_amount=expense.amount,
        currency=expense.currency,
        order_date=expense.expense_date,
        description=expense.description or expense.category,
    )


def _expense_to_payment(expense: Any) -> PortalSupplierPayment:
    reference = expense.description or str(expense.id)
    paid_at = expense.expense_date.isoformat() if getattr(expense, "expense_date", None) else None
    return PortalSupplierPayment(
        id=expense.id,
        reference=reference,
        amount=expense.amount,
        currency=expense.currency,
        paid_at=paid_at,
        status="RECORDED",
        description=expense.description,
    )


async def _validate_portal_token_or_error(
    session: AsyncSession,
    token: str,
    expected_type: PortalEntityType | None = None,
) -> tuple[PortalEntityType, Any, Any]:
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


async def _get_customer_and_invoices(
    session: AsyncSession, tenant_id: UUID, customer_id: UUID
) -> tuple[CustomerPublic, list[InvoicePublic]]:
    customer, invoices = await customer_service.get_customer_with_open_invoices(session, tenant_id, customer_id)
    if not customer:
        raise AppException(
            code="customer_not_found", message="Customer not found", http_status=status.HTTP_404_NOT_FOUND
        )
    invoice_models = [InvoicePublic.model_validate(inv) for inv in invoices]
    return CustomerPublic.model_validate(customer), invoice_models


async def _get_customer_payments(
    session: AsyncSession, tenant_id: UUID, customer_id: UUID
) -> list[PaymentPublic]:
    payments = await payment_service.list_payments_for_customer(session, tenant_id, customer_id)
    return [PaymentPublic.model_validate(payment) for payment in payments]


async def _get_supplier_and_expenses(
    session: AsyncSession, tenant_id: UUID, supplier_id: UUID
) -> tuple[SupplierPublic, list[PortalOrder], list[PortalSupplierPayment]]:
    supplier, expenses = await supplier_service.get_supplier_with_expenses(session, tenant_id, supplier_id)
    if not supplier:
        raise AppException(
            code="supplier_not_found", message="Supplier not found", http_status=status.HTTP_404_NOT_FOUND
        )
    orders = [_expense_to_order(expense) for expense in expenses]
    payments = [_expense_to_payment(expense) for expense in expenses]
    return SupplierPublic.model_validate(supplier), orders, payments


@router.post("/customer/token", response_model=PortalTokenResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_portal_token(
    payload: PortalTokenRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    settings=Depends(deps.get_settings),
):
    await _portal_rate_limit(request, settings, key="portal")
    if not payload.customer_id:
        raise AppException(
            code="customer_required", message="customer_id is required", http_status=status.HTTP_400_BAD_REQUEST
        )
    customer = await customer_service.get_customer(session, tenant_id, payload.customer_id)
    if not customer or getattr(customer, "is_deleted", False):
        raise AppException(
            code="customer_not_found", message="Customer not found", http_status=status.HTTP_404_NOT_FOUND
        )

    expires_at = _token_expiry(payload.expires_in)
    raw_token, token = await portal_service.create_portal_token_for_customer(
        session, tenant_id, payload.customer_id, expires_at
    )
    relative_url = f"/portal/customer/{raw_token}"
    portal_url = email_service.build_frontend_url(relative_url, settings=settings)

    is_production = (settings.environment or "").lower() == "production"
    recipient_email = getattr(customer, "email", None)

    if is_production:
        if not recipient_email:
            raise AppException(
                code="customer_email_missing",
                message="Customer has no email to send portal link.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            await email_service.send_portal_link_email(
                to_email=recipient_email,
                portal_url=portal_url,
                settings=settings,
                audience="customer",
                display_name=getattr(customer, "name", None),
            )
        except Exception as exc:  # pragma: no cover - external dependency path
            logger.exception("Failed to send customer portal email for %s", customer.id)
            raise AppException(
                code="portal_email_failed",
                message="Failed to email portal link",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from exc
        return PortalTokenResponse(success=True, message="Portal link sent via email.")

    # Development / testing: return the URL for manual testing.
    return PortalTokenResponse(success=True, url=portal_url, expires_at=token.expires_at, token_id=token.id)


@router.post("/supplier/token", response_model=PortalTokenResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier_portal_token(
    payload: PortalTokenRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    _: User = Depends(deps.get_current_active_user),
    settings=Depends(deps.get_settings),
):
    await _portal_rate_limit(request, settings, key="portal")
    if not payload.supplier_id:
        raise AppException(
            code="supplier_required", message="supplier_id is required", http_status=status.HTTP_400_BAD_REQUEST
        )
    supplier = await supplier_service.get_supplier(session, tenant_id, payload.supplier_id)
    if not supplier or getattr(supplier, "is_deleted", False):
        raise AppException(
            code="supplier_not_found", message="Supplier not found", http_status=status.HTTP_404_NOT_FOUND
        )

    expires_at = _token_expiry(payload.expires_in)
    raw_token, token = await portal_service.create_portal_token_for_supplier(
        session, tenant_id, payload.supplier_id, expires_at
    )
    relative_url = f"/portal/supplier/{raw_token}"
    portal_url = email_service.build_frontend_url(relative_url, settings=settings)

    is_production = (settings.environment or "").lower() == "production"
    recipient_email = getattr(supplier, "email", None)

    if is_production:
        if not recipient_email:
            raise AppException(
                code="supplier_email_missing",
                message="Supplier has no email to send portal link.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            await email_service.send_portal_link_email(
                to_email=recipient_email,
                portal_url=portal_url,
                settings=settings,
                audience="supplier",
                display_name=getattr(supplier, "name", None),
            )
        except Exception as exc:  # pragma: no cover - external dependency path
            logger.exception("Failed to send supplier portal email for %s", supplier.id)
            raise AppException(
                code="portal_email_failed",
                message="Failed to email portal link",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from exc
        return PortalTokenResponse(success=True, message="Portal link sent via email.")

    # Development / testing: return the URL for manual testing.
    return PortalTokenResponse(success=True, url=portal_url, expires_at=token.expires_at, token_id=token.id)


@router.get("/customer/{token}", response_model=CustomerPortalResponse)
async def get_customer_portal(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    await _portal_rate_limit(request, settings)
    _, _, portal_token = await _validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.CUSTOMER
    )
    try:
        request.state.tenant_id = portal_token.tenant_id
    except Exception:
        pass

    customer_model, invoices = await _get_customer_and_invoices(
        session, portal_token.tenant_id, portal_token.entity_id
    )
    payment_models = await _get_customer_payments(session, portal_token.tenant_id, portal_token.entity_id)
    recent_candidates: list[PortalActivityItem] = [
        _invoice_activity_item(inv) for inv in invoices
    ] + [_payment_activity_item(payment) for payment in payment_models]
    settings_payload = await _load_portal_settings(session, portal_token.tenant_id, PortalEntityType.CUSTOMER)
    recent_activity = _build_recent_activity(recent_candidates)
    return CustomerPortalResponse(
        customer=customer_model,
        invoices=invoices,
        payments=payment_models,
        settings=settings_payload,
        recent_activity=recent_activity,
    )


@router.get("/customer/{token}/invoices", response_model=CustomerInvoicesResponse)
async def get_customer_portal_invoices(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
) -> CustomerInvoicesResponse:
    await _portal_rate_limit(request, settings)
    _, _, portal_token = await _validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.CUSTOMER
    )
    _, invoices = await _get_customer_and_invoices(session, portal_token.tenant_id, portal_token.entity_id)
    return CustomerInvoicesResponse(invoices=invoices)


@router.get("/customer/{token}/payments", response_model=CustomerPaymentsResponse)
async def get_customer_portal_payments(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
) -> CustomerPaymentsResponse:
    await _portal_rate_limit(request, settings)
    _, _, portal_token = await _validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.CUSTOMER
    )
    payments = await _get_customer_payments(session, portal_token.tenant_id, portal_token.entity_id)
    return CustomerPaymentsResponse(payments=payments)


@router.get("/customer/{token}/settings", response_model=PortalSettings)
async def get_customer_portal_settings(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
) -> PortalSettings:
    await _portal_rate_limit(request, settings)
    _, _, portal_token = await _validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.CUSTOMER
    )
    return await _load_portal_settings(session, portal_token.tenant_id, PortalEntityType.CUSTOMER)


@router.get("/supplier/{token}", response_model=SupplierPortalResponse)
async def get_supplier_portal(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    await _portal_rate_limit(request, settings)
    _, _, portal_token = await _validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.SUPPLIER
    )
    try:
        request.state.tenant_id = portal_token.tenant_id
    except Exception:
        pass

    supplier_model, orders, payments = await _get_supplier_and_expenses(
        session, portal_token.tenant_id, portal_token.entity_id
    )
    activity_candidates = [_order_activity_item(order) for order in orders] + [
        _supplier_payment_activity_item(payment) for payment in payments
    ]
    settings_payload = await _load_portal_settings(session, portal_token.tenant_id, PortalEntityType.SUPPLIER)
    recent_activity = _build_recent_activity(activity_candidates)
    return SupplierPortalResponse(
        supplier=supplier_model,
        orders=orders,
        payments=payments,
        settings=settings_payload,
        recent_activity=recent_activity,
    )


@router.get("/supplier/{token}/orders", response_model=SupplierOrdersResponse)
async def get_supplier_portal_orders(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
) -> SupplierOrdersResponse:
    await _portal_rate_limit(request, settings)
    _, _, portal_token = await _validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.SUPPLIER
    )
    _, orders, _ = await _get_supplier_and_expenses(session, portal_token.tenant_id, portal_token.entity_id)
    return SupplierOrdersResponse(orders=orders)


@router.get("/supplier/{token}/payments", response_model=SupplierPaymentsResponse)
async def get_supplier_portal_payments(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
) -> SupplierPaymentsResponse:
    await _portal_rate_limit(request, settings)
    _, _, portal_token = await _validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.SUPPLIER
    )
    _, _, payments = await _get_supplier_and_expenses(session, portal_token.tenant_id, portal_token.entity_id)
    return SupplierPaymentsResponse(payments=payments)


@router.get("/supplier/{token}/settings", response_model=PortalSettings)
async def get_supplier_portal_settings(
    token: str,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
) -> PortalSettings:
    await _portal_rate_limit(request, settings)
    _, _, portal_token = await _validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.SUPPLIER
    )
    return await _load_portal_settings(session, portal_token.tenant_id, PortalEntityType.SUPPLIER)


@router.patch("/customer/{token}/settings", response_model=PortalSettings)
async def update_customer_portal_settings(
    token: str,
    payload: PortalSettingsUpdate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    await _portal_rate_limit(request, settings)
    _, _, portal_token = await _validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.CUSTOMER
    )
    return await _persist_portal_settings(
        session, portal_token.tenant_id, PortalEntityType.CUSTOMER, payload
    )


@router.patch("/supplier/{token}/settings", response_model=PortalSettings)
async def update_supplier_portal_settings(
    token: str,
    payload: PortalSettingsUpdate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    await _portal_rate_limit(request, settings)
    _, _, portal_token = await _validate_portal_token_or_error(
        session, token, expected_type=PortalEntityType.SUPPLIER
    )
    return await _persist_portal_settings(
        session, portal_token.tenant_id, PortalEntityType.SUPPLIER, payload
    )


__all__ = ["router"]
