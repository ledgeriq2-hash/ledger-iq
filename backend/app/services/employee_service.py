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
from app.models.employee import Employee, EmployeeStatus
from app.schemas.employee import EmployeeStatusFilter
from app.services import audit_log_service


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_employees(
    session: AsyncSession,
    tenant_id: UUID,
    params: PaginationParams,
    *,
    search: str | None = None,
    status_filter: EmployeeStatusFilter | None = None,
    include_deleted: bool = False,
) -> tuple[list[Employee], int]:
    statement = select(Employee).where(Employee.tenant_id == tenant_id)
    if search:
        term = search.strip()
        if term:
            pattern = f"%{term}%"
            statement = statement.where(
                or_(
                    Employee.code.ilike(pattern),
                    Employee.name.ilike(pattern),
                    Employee.email.ilike(pattern),
                )
            )
    if status_filter is not None and status_filter != EmployeeStatusFilter.ALL:
        statement = statement.where(Employee.status == EmployeeStatus(status_filter.value))
    elif not include_deleted:
        statement = statement.where(Employee.status != EmployeeStatus.DELETED)
    statement = statement.order_by(Employee.created_at.desc())
    return await paginate_query(session, statement, params)


async def get_employee(
    session: AsyncSession,
    tenant_id: UUID,
    employee_id: UUID,
    *,
    include_deleted: bool = False,
) -> Employee | None:
    statement = select(Employee).where(Employee.id == employee_id, Employee.tenant_id == tenant_id)
    if not include_deleted:
        statement = statement.where(Employee.status != EmployeeStatus.DELETED)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


def _audit_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, EmployeeStatus):
        return value.value
    return value


def _audit_payload(employee: Employee) -> dict[str, Any]:
    return {
        "code": employee.code,
        "name": employee.name,
        "email": employee.email,
        "phone": employee.phone,
        "address": employee.address,
        "tax_id": employee.tax_id,
        "balance": str(employee.balance),
        "status": _audit_value(employee.status),
        "deleted_at": _audit_value(employee.deleted_at),
        "deactivated_at": _audit_value(employee.deactivated_at),
    }


async def create_employee(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> Employee:
    data = _to_dict(payload)
    data.pop("status", None)
    data.pop("deleted_at", None)
    data.pop("deactivated_at", None)
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    if not code:
        raise AppException(code="employee_code_required", message="Employee code is required", http_status=422)
    if not name:
        raise AppException(code="employee_name_required", message="Employee name is required", http_status=422)
    data["code"] = code
    data["name"] = name
    existing = await session.execute(
        select(Employee.id).where(Employee.tenant_id == tenant_id, Employee.code == data.get("code"))
    )
    if existing.scalar_one_or_none():
        raise AppException(code="employee_code_exists", message="Employee code already exists", http_status=409)
    employee = Employee(**data, tenant_id=tenant_id)
    session.add(employee)
    try:
        await session.flush()
        await audit_log_service.record_audit_log(
            session,
            tenant_id,
            "employees",
            str(employee.id),
            "EMPLOYEE.CREATE",
            user_id=actor_id,
            new_data=_audit_payload(employee),
            commit=False,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_employees_tenant_code" in message or "employees_tenant_id_code" in message:
            raise AppException(
                code="employee_code_exists",
                message="Employee code already exists",
                http_status=409,
            ) from exc
        raise
    await session.refresh(employee)
    return employee


async def update_employee(
    session: AsyncSession,
    tenant_id: UUID,
    employee_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> Employee | None:
    employee = await get_employee(session, tenant_id, employee_id, include_deleted=True)
    if not employee:
        return None
    if employee.status == EmployeeStatus.DELETED:
        raise AppException(code="employee_deleted", message="Employee is deleted", http_status=409)
    data = _to_dict(payload, exclude_unset=True)
    allowed_fields = {"name", "email", "phone", "address", "tax_id", "balance"}
    changes = {field: value for field, value in data.items() if field in allowed_fields}
    if not changes:
        return employee
    old_data = {field: _audit_value(getattr(employee, field)) for field in changes}
    for field, value in changes.items():
        setattr(employee, field, value)
    await session.flush()
    new_data = {field: _audit_value(getattr(employee, field)) for field in changes}
    await audit_log_service.record_audit_log(
        session,
        tenant_id,
        "employees",
        str(employee.id),
        "EMPLOYEE.UPDATE",
        user_id=actor_id,
        old_data=old_data,
        new_data=new_data,
        commit=False,
    )
    await session.commit()
    await session.refresh(employee)
    return employee


async def deactivate_employee(
    session: AsyncSession,
    tenant_id: UUID,
    employee_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> Employee | None:
    employee = await get_employee(session, tenant_id, employee_id, include_deleted=True)
    if not employee:
        return None
    if employee.status == EmployeeStatus.DELETED:
        raise AppException(code="employee_deleted", message="Employee is deleted", http_status=409)
    if employee.status != EmployeeStatus.INACTIVE:
        old_status = employee.status
        employee.status = EmployeeStatus.INACTIVE
        employee.deactivated_at = datetime.now(UTC)
        await session.flush()
        await audit_log_service.record_audit_log(
            session,
            tenant_id,
            "employees",
            str(employee.id),
            "EMPLOYEE.DEACTIVATE",
            user_id=actor_id,
            old_data={"status": _audit_value(old_status)},
            new_data={
                "status": _audit_value(employee.status),
                "deactivated_at": _audit_value(employee.deactivated_at),
            },
            commit=False,
        )
        await session.commit()
        await session.refresh(employee)
    return employee


async def reactivate_employee(
    session: AsyncSession,
    tenant_id: UUID,
    employee_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> Employee | None:
    employee = await get_employee(session, tenant_id, employee_id, include_deleted=True)
    if not employee:
        return None
    if employee.status == EmployeeStatus.DELETED:
        raise AppException(code="employee_deleted", message="Employee is deleted", http_status=409)
    if employee.status != EmployeeStatus.ACTIVE:
        old_status = employee.status
        employee.status = EmployeeStatus.ACTIVE
        employee.deactivated_at = None
        await session.flush()
        await audit_log_service.record_audit_log(
            session,
            tenant_id,
            "employees",
            str(employee.id),
            "EMPLOYEE.REACTIVATE",
            user_id=actor_id,
            old_data={"status": _audit_value(old_status)},
            new_data={"status": _audit_value(employee.status)},
            commit=False,
        )
        await session.commit()
        await session.refresh(employee)
    return employee


async def soft_delete_employee(
    session: AsyncSession,
    tenant_id: UUID,
    employee_id: UUID,
    *,
    actor_id: UUID | None = None,
) -> bool:
    employee = await get_employee(session, tenant_id, employee_id, include_deleted=True)
    if not employee:
        return False
    if employee.status == EmployeeStatus.DELETED:
        return True
    previous_status = employee.status
    employee.status = EmployeeStatus.DELETED
    employee.deleted_at = datetime.now(UTC)
    employee.deactivated_at = employee.deactivated_at or None
    await session.flush()
    await audit_log_service.record_audit_log(
        session,
        tenant_id,
        "employees",
        str(employee.id),
        "EMPLOYEE.SOFT_DELETE",
        user_id=actor_id,
        old_data={"status": _audit_value(previous_status)},
        new_data={
            "status": EmployeeStatus.DELETED.value,
            "deleted_at": _audit_value(employee.deleted_at),
        },
        commit=False,
    )
    await session.commit()
    await session.refresh(employee)
    return True


async def validate_can_receive_movements(
    session: AsyncSession,
    tenant_id: UUID,
    employee_id: UUID,
) -> Employee:
    result = await session.execute(
        select(Employee).where(Employee.id == employee_id, Employee.tenant_id == tenant_id)
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise AppException(code="employee_not_found", message="Employee not found", http_status=404)
    if employee.status == EmployeeStatus.DELETED:
        raise AppException(code="employee_deleted", message="Employee is deleted", http_status=409)
    if employee.status == EmployeeStatus.INACTIVE:
        raise AppException(code="employee_inactive", message="Employee is inactive", http_status=409)
    return employee


__all__ = [
    "list_employees",
    "get_employee",
    "create_employee",
    "update_employee",
    "deactivate_employee",
    "reactivate_employee",
    "soft_delete_employee",
    "validate_can_receive_movements",
]
