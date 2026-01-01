from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams, paginate_query
from app.core.exceptions import AppException
from app.models.expense import Expense
from app.models.supplier import Supplier, SupplierStatus
from app.schemas.supplier import SupplierStatusFilter
from app.services import audit_log_service


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_suppliers(
    session: AsyncSession,
    tenant_id: UUID,
    params: PaginationParams,
    *,
    search: str | None = None,
    status_filter: SupplierStatusFilter | None = None,
    include_deleted: bool = False,
) -> tuple[list[Supplier], int]:
    statement = select(Supplier).where(Supplier.tenant_id == tenant_id)
    if search:
        term = search.strip()
        if term:
            pattern = f"%{term}%"
            statement = statement.where(or_(Supplier.code.ilike(pattern), Supplier.name.ilike(pattern)))
    if status_filter is not None and status_filter != SupplierStatusFilter.ALL:
        statement = statement.where(Supplier.status == SupplierStatus(status_filter.value))
    elif not include_deleted:
        statement = statement.where(Supplier.status != SupplierStatus.DELETED)
    statement = statement.order_by(Supplier.created_at.desc())
    return await paginate_query(session, statement, params)


async def get_supplier(
    session: AsyncSession,
    tenant_id: UUID,
    supplier_id: UUID,
    *,
    include_deleted: bool = False,
) -> Supplier | None:
    statement = select(Supplier).where(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id)
    if not include_deleted:
        statement = statement.where(Supplier.status != SupplierStatus.DELETED)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


def _audit_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, SupplierStatus):
        return value.value
    return value


def _audit_payload(supplier: Supplier) -> dict[str, Any]:
    return {
        "code": supplier.code,
        "name": supplier.name,
        "email": supplier.email,
        "phone": supplier.phone,
        "address": supplier.address,
        "tax_id": supplier.tax_id,
        "balance": str(supplier.balance),
        "status": _audit_value(supplier.status),
        "deleted_at": _audit_value(supplier.deleted_at),
        "deactivated_at": _audit_value(supplier.deactivated_at),
    }


async def create_supplier(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> Supplier:
    data = _to_dict(payload)
    data.pop("status", None)
    data.pop("deleted_at", None)
    data.pop("deactivated_at", None)
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    if not code:
        raise AppException(code="supplier_code_required", message="Supplier code is required", http_status=422)
    if not name:
        raise AppException(code="supplier_name_required", message="Supplier name is required", http_status=422)
    data["code"] = code
    data["name"] = name
    existing = await session.execute(
        select(Supplier.id).where(Supplier.tenant_id == tenant_id, Supplier.code == data.get("code"))
    )
    if existing.scalar_one_or_none():
        raise AppException(code="supplier_code_exists", message="Supplier code already exists", http_status=409)
    supplier = Supplier(**data, tenant_id=tenant_id)
    session.add(supplier)
    try:
        await session.flush()
        await audit_log_service.record_audit_log(
            session,
            tenant_id,
            "suppliers",
            str(supplier.id),
            "SUPPLIER.CREATE",
            user_id=actor_id,
            new_data=_audit_payload(supplier),
            commit=False,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_suppliers_tenant_code" in message or "suppliers_tenant_id_code" in message:
            raise AppException(
                code="supplier_code_exists",
                message="Supplier code already exists",
                http_status=409,
            ) from exc
        raise
    await session.refresh(supplier)
    return supplier


async def update_supplier(
    session: AsyncSession,
    tenant_id: UUID,
    supplier_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> Supplier | None:
    supplier = await get_supplier(session, tenant_id, supplier_id, include_deleted=True)
    if not supplier:
        return None
    if supplier.status == SupplierStatus.DELETED:
        raise AppException(code="supplier_deleted", message="Supplier is deleted", http_status=409)
    data = _to_dict(payload, exclude_unset=True)
    allowed_fields = {"name", "email", "phone", "address", "tax_id", "balance"}
    changes = {field: value for field, value in data.items() if field in allowed_fields}
    if not changes:
        return supplier
    old_data = {field: _audit_value(getattr(supplier, field)) for field in changes}
    for field, value in changes.items():
        setattr(supplier, field, value)
    await session.flush()
    new_data = {field: _audit_value(getattr(supplier, field)) for field in changes}
    await audit_log_service.record_audit_log(
        session,
        tenant_id,
        "suppliers",
        str(supplier.id),
        "SUPPLIER.UPDATE",
        user_id=actor_id,
        old_data=old_data,
        new_data=new_data,
        commit=False,
    )
    await session.commit()
    await session.refresh(supplier)
    return supplier


async def deactivate_supplier(
    session: AsyncSession,
    tenant_id: UUID,
    supplier_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> Supplier | None:
    supplier = await get_supplier(session, tenant_id, supplier_id, include_deleted=True)
    if not supplier:
        return None
    if supplier.status == SupplierStatus.DELETED:
        raise AppException(code="supplier_deleted", message="Supplier is deleted", http_status=409)
    if supplier.status != SupplierStatus.INACTIVE:
        old_status = supplier.status
        supplier.status = SupplierStatus.INACTIVE
        supplier.deactivated_at = datetime.now(UTC)
        await session.flush()
        await audit_log_service.record_audit_log(
            session,
            tenant_id,
            "suppliers",
            str(supplier.id),
            "SUPPLIER.DEACTIVATE",
            user_id=actor_id,
            old_data={"status": _audit_value(old_status)},
            new_data={
                "status": _audit_value(supplier.status),
                "deactivated_at": _audit_value(supplier.deactivated_at),
            },
            commit=False,
        )
        await session.commit()
        await session.refresh(supplier)
    return supplier


async def reactivate_supplier(
    session: AsyncSession,
    tenant_id: UUID,
    supplier_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> Supplier | None:
    supplier = await get_supplier(session, tenant_id, supplier_id, include_deleted=True)
    if not supplier:
        return None
    if supplier.status == SupplierStatus.DELETED:
        raise AppException(code="supplier_deleted", message="Supplier is deleted", http_status=409)
    if supplier.status != SupplierStatus.ACTIVE:
        old_status = supplier.status
        supplier.status = SupplierStatus.ACTIVE
        supplier.deactivated_at = None
        await session.flush()
        await audit_log_service.record_audit_log(
            session,
            tenant_id,
            "suppliers",
            str(supplier.id),
            "SUPPLIER.REACTIVATE",
            user_id=actor_id,
            old_data={"status": _audit_value(old_status)},
            new_data={"status": _audit_value(supplier.status)},
            commit=False,
        )
        await session.commit()
        await session.refresh(supplier)
    return supplier


async def soft_delete_supplier(
    session: AsyncSession,
    tenant_id: UUID,
    supplier_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> bool:
    supplier = await get_supplier(session, tenant_id, supplier_id, include_deleted=True)
    if not supplier:
        return False
    if supplier.status == SupplierStatus.DELETED:
        return True
    previous_status = supplier.status
    supplier.status = SupplierStatus.DELETED
    supplier.deleted_at = datetime.now(UTC)
    supplier.deactivated_at = supplier.deactivated_at or None
    await session.flush()
    await audit_log_service.record_audit_log(
        session,
        tenant_id,
        "suppliers",
        str(supplier.id),
        "SUPPLIER.SOFT_DELETE",
        user_id=actor_id,
        old_data={"status": _audit_value(previous_status)},
        new_data={
            "status": SupplierStatus.DELETED.value,
            "deleted_at": _audit_value(supplier.deleted_at),
        },
        commit=False,
    )
    await session.commit()
    await session.refresh(supplier)
    return True


async def validate_can_receive_movements(
    session: AsyncSession,
    tenant_id: UUID,
    supplier_id: UUID,
) -> Supplier:
    result = await session.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.tenant_id == tenant_id)
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise AppException(code="supplier_not_found", message="Supplier not found", http_status=404)
    if supplier.status == SupplierStatus.DELETED:
        raise AppException(code="supplier_deleted", message="Supplier is deleted", http_status=409)
    if supplier.status == SupplierStatus.INACTIVE:
        raise AppException(code="supplier_inactive", message="Supplier is inactive", http_status=409)
    return supplier


async def get_supplier_with_expenses(
    session: AsyncSession, tenant_id: UUID, supplier_id: UUID
) -> tuple[Supplier | None, Sequence[Expense]]:
    supplier = await get_supplier(session, tenant_id, supplier_id)
    if not supplier:
        return None, []
    expenses_result = await session.execute(
        select(Expense).where(Expense.tenant_id == tenant_id, Expense.supplier_id == supplier_id)
    )
    expenses = expenses_result.scalars().all()
    return supplier, expenses


__all__ = [
    "list_suppliers",
    "get_supplier",
    "create_supplier",
    "update_supplier",
    "deactivate_supplier",
    "reactivate_supplier",
    "soft_delete_supplier",
    "validate_can_receive_movements",
    "get_supplier_with_expenses",
]
