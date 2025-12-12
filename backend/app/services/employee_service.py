from __future__ import annotations

from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_employees(session: AsyncSession, tenant_id: UUID) -> Sequence[Employee]:
    result = await session.execute(select(Employee).where(Employee.tenant_id == tenant_id))
    return result.scalars().all()


async def get_employee(session: AsyncSession, tenant_id: UUID, employee_id: UUID) -> Employee | None:
    result = await session.execute(
        select(Employee).where(Employee.id == employee_id, Employee.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_employee(session: AsyncSession, tenant_id: UUID, payload: Any) -> Employee:
    data = _to_dict(payload)
    employee = Employee(**data, tenant_id=tenant_id)
    session.add(employee)
    await session.commit()
    await session.refresh(employee)
    return employee


async def update_employee(
    session: AsyncSession, tenant_id: UUID, employee_id: UUID, payload: Any
) -> Employee | None:
    employee = await get_employee(session, tenant_id, employee_id)
    if not employee:
        return None
    data = _to_dict(payload, exclude_unset=True)
    for field, value in data.items():
        if field in {"id", "tenant_id"}:
            continue
        setattr(employee, field, value)
    await session.commit()
    await session.refresh(employee)
    return employee


async def delete_employee(session: AsyncSession, tenant_id: UUID, employee_id: UUID) -> bool:
    result = await session.execute(
        delete(Employee).where(Employee.id == employee_id, Employee.tenant_id == tenant_id)
    )
    await session.commit()
    return result.rowcount > 0


__all__ = [
    "list_employees",
    "get_employee",
    "create_employee",
    "update_employee",
    "delete_employee",
]
