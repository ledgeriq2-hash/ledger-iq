from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.pagination import PaginationParams, paginate_query
from app.models.customer import Customer, CustomerStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.customer import CustomerStatusFilter
from app.services import audit_log_service, usage_service


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_customers(
    session: AsyncSession,
    tenant_id: UUID,
    params: PaginationParams,
    *,
    search: str | None = None,
    status_filter: CustomerStatusFilter | None = None,
) -> tuple[list[Customer], int]:
    statement = select(Customer).where(Customer.tenant_id == tenant_id)
    if search:
        term = search.strip()
        if term:
            pattern = f"%{term}%"
            statement = statement.where(or_(Customer.code.ilike(pattern), Customer.name.ilike(pattern)))
    if status_filter is None:
        statement = statement.where(Customer.status != CustomerStatus.DELETED)
    elif status_filter != CustomerStatusFilter.ALL:
        statement = statement.where(Customer.status == CustomerStatus(status_filter.value))
    statement = statement.order_by(Customer.created_at.desc())
    return await paginate_query(session, statement, params)


async def get_customer(
    session: AsyncSession,
    tenant_id: UUID,
    customer_id: UUID,
    *,
    include_deleted: bool = False,
) -> Customer | None:
    statement = select(Customer).where(Customer.id == customer_id, Customer.tenant_id == tenant_id)
    if not include_deleted:
        statement = statement.where(Customer.status != CustomerStatus.DELETED)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


def _audit_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, CustomerStatus):
        return value.value
    return value


def _audit_payload(customer: Customer) -> dict[str, Any]:
    return {
        "code": customer.code,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "tax_id": customer.tax_id,
        "currency_code": customer.currency_code,
        "payment_terms_days": customer.payment_terms_days,
        "notes": customer.notes,
        "metadata": customer.metadata_json,
        "status": _audit_value(customer.status),
        "deleted_at": _audit_value(customer.deleted_at),
    }


async def create_customer(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> Customer:
    data = _to_dict(payload)
    if "metadata" in data and "metadata_json" not in data:
        data["metadata_json"] = data.pop("metadata")
    status = data.get("status")
    if status is not None:
        try:
            status = CustomerStatus(status)
        except Exception as exc:
            raise AppException(
                code="customer_status_invalid",
                message="Customer status is invalid",
                http_status=422,
            ) from exc
        if status == CustomerStatus.DELETED:
            raise AppException(
                code="customer_status_invalid",
                message="Customer status is invalid",
                http_status=422,
            )
        data["status"] = status
    data.pop("deleted_at", None)
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    if not code:
        raise AppException(
            code="customer_code_required",
            message="Customer code is required",
            http_status=422,
        )
    if not name:
        raise AppException(
            code="customer_name_required",
            message="Customer name is required",
            http_status=422,
        )
    data["code"] = code
    data["name"] = name
    existing = await session.execute(
        select(Customer.id).where(Customer.tenant_id == tenant_id, Customer.code == data.get("code"))
    )
    if existing.scalar_one_or_none():
        raise AppException(
            code="customer_code_exists",
            message="Customer code already exists",
            http_status=409,
        )
    customer = Customer(**data, tenant_id=tenant_id)
    session.add(customer)
    try:
        await session.flush()
        await usage_service.record_customer_created(session, tenant_id, commit=False)
        await audit_log_service.record_audit_log(
            session,
            tenant_id,
            "customers",
            str(customer.id),
            "CUSTOMER.CREATE",
            user_id=actor_id,
            new_data=_audit_payload(customer),
            commit=False,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_customers_tenant_code" in message or "customers_tenant_id_code" in message:
            raise AppException(
                code="customer_code_exists",
                message="Customer code already exists",
                http_status=409,
            ) from exc
        raise
    await session.refresh(customer)
    return customer


async def update_customer(
    session: AsyncSession,
    tenant_id: UUID,
    customer_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> Customer | None:
    customer = await get_customer(session, tenant_id, customer_id, include_deleted=True)
    if not customer:
        return None
    if customer.status == CustomerStatus.DELETED:
        raise AppException(
            code="customer_deleted",
            message="Customer is deleted",
            http_status=409,
        )
    data = _to_dict(payload, exclude_unset=True)
    if "metadata" in data and "metadata_json" not in data:
        data["metadata_json"] = data.pop("metadata")
    allowed_fields = {
        "code",
        "name",
        "email",
        "phone",
        "tax_id",
        "currency_code",
        "payment_terms_days",
        "notes",
        "metadata_json",
        "status",
    }
    changes = {field: value for field, value in data.items() if field in allowed_fields}
    if not changes:
        return customer
    if "code" in changes:
        code = (changes.get("code") or "").strip()
        if not code:
            raise AppException(
                code="customer_code_required",
                message="Customer code is required",
                http_status=422,
            )
        existing = await session.execute(
            select(Customer.id).where(
                Customer.tenant_id == tenant_id,
                Customer.code == code,
                Customer.id != customer_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="customer_code_exists",
                message="Customer code already exists",
                http_status=409,
            )
        changes["code"] = code
    if "status" in changes and changes["status"] is not None:
        try:
            status = CustomerStatus(changes["status"])
        except Exception as exc:
            raise AppException(
                code="customer_status_invalid",
                message="Customer status is invalid",
                http_status=422,
            ) from exc
        if status == CustomerStatus.DELETED:
            raise AppException(
                code="customer_status_invalid",
                message="Customer status is invalid",
                http_status=422,
            )
        changes["status"] = status
    old_data = {
        ("metadata" if field == "metadata_json" else field): _audit_value(getattr(customer, field))
        for field in changes
    }
    for field, value in changes.items():
        setattr(customer, field, value)
    try:
        await session.flush()
        new_data = {
            ("metadata" if field == "metadata_json" else field): _audit_value(getattr(customer, field))
            for field in changes
        }
        await audit_log_service.record_audit_log(
            session,
            tenant_id,
            "customers",
            str(customer.id),
            "CUSTOMER.UPDATE",
            user_id=actor_id,
            old_data=old_data,
            new_data=new_data,
            commit=False,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_customers_tenant_code" in message or "customers_tenant_id_code" in message:
            raise AppException(
                code="customer_code_exists",
                message="Customer code already exists",
                http_status=409,
            ) from exc
        raise
    await session.refresh(customer)
    return customer


async def deactivate_customer(
    session: AsyncSession,
    tenant_id: UUID,
    customer_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> Customer | None:
    customer = await get_customer(session, tenant_id, customer_id, include_deleted=True)
    if not customer:
        return None
    if customer.status == CustomerStatus.DELETED:
        raise AppException(code="customer_deleted", message="Customer is deleted", http_status=409)
    if customer.status != CustomerStatus.INACTIVE:
        old_status = customer.status
        customer.status = CustomerStatus.INACTIVE
        await session.flush()
        await audit_log_service.record_audit_log(
            session,
            tenant_id,
            "customers",
            str(customer.id),
            "CUSTOMER.DEACTIVATE",
            user_id=actor_id,
            old_data={"status": _audit_value(old_status)},
            new_data={"status": _audit_value(customer.status)},
            commit=False,
        )
        await session.commit()
        await session.refresh(customer)
    return customer


async def reactivate_customer(
    session: AsyncSession,
    tenant_id: UUID,
    customer_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> Customer | None:
    customer = await get_customer(session, tenant_id, customer_id, include_deleted=True)
    if not customer:
        return None
    if customer.status == CustomerStatus.DELETED:
        raise AppException(code="customer_deleted", message="Customer is deleted", http_status=409)
    if customer.status != CustomerStatus.ACTIVE:
        old_status = customer.status
        customer.status = CustomerStatus.ACTIVE
        await session.flush()
        await audit_log_service.record_audit_log(
            session,
            tenant_id,
            "customers",
            str(customer.id),
            "CUSTOMER.REACTIVATE",
            user_id=actor_id,
            old_data={"status": _audit_value(old_status)},
            new_data={"status": _audit_value(customer.status)},
            commit=False,
        )
        await session.commit()
        await session.refresh(customer)
    return customer


async def delete_customer(
    session: AsyncSession,
    tenant_id: UUID,
    customer_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> bool:
    customer = await get_customer(session, tenant_id, customer_id, include_deleted=True)
    if not customer:
        return False
    if customer.status == CustomerStatus.DELETED:
        return False
    previous_status = customer.status
    customer.status = CustomerStatus.DELETED
    customer.deleted_at = datetime.now(UTC)
    await session.flush()
    await audit_log_service.record_audit_log(
        session,
        tenant_id,
        "customers",
        str(customer.id),
        "CUSTOMER.SOFT_DELETE",
        user_id=actor_id,
        old_data={"status": _audit_value(previous_status)},
        new_data={
            "status": CustomerStatus.DELETED.value,
            "deleted_at": _audit_value(customer.deleted_at),
        },
        commit=False,
    )
    await session.commit()
    return True


async def get_customer_with_open_invoices(
    session: AsyncSession, tenant_id: UUID, customer_id: UUID
) -> tuple[Customer | None, Sequence[Invoice]]:
    customer = await get_customer(session, tenant_id, customer_id)
    if not customer:
        return None, []
    invoices_result = await session.execute(
        select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.customer_id == customer_id,
            Invoice.status.notin_([InvoiceStatus.PAID, InvoiceStatus.CANCELLED]),
        )
    )
    invoices = invoices_result.scalars().all()
    return customer, invoices


__all__ = [
    "list_customers",
    "get_customer",
    "create_customer",
    "update_customer",
    "deactivate_customer",
    "reactivate_customer",
    "delete_customer",
    "get_customer_with_open_invoices",
]
