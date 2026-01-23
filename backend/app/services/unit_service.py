from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.pagination import PaginationParams, paginate_query
from app.models.unit import Unit


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_units(
    session: AsyncSession,
    tenant_id: UUID,
    params: PaginationParams,
) -> tuple[list[Unit], int]:
    statement = select(Unit).where(Unit.tenant_id == tenant_id).order_by(Unit.code.asc())
    return await paginate_query(session, statement, params)


async def get_unit(session: AsyncSession, tenant_id: UUID, unit_id: UUID) -> Unit | None:
    result = await session.execute(
        select(Unit).where(Unit.id == unit_id, Unit.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_unit(session: AsyncSession, tenant_id: UUID, payload: Any) -> Unit:
    data = _to_dict(payload)
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    if not code:
        raise AppException(code="unit_code_required", message="Unit code is required", http_status=422)
    if not name:
        raise AppException(code="unit_name_required", message="Unit name is required", http_status=422)
    data["code"] = code
    data["name"] = name

    existing = await session.execute(
        select(Unit.id).where(Unit.tenant_id == tenant_id, Unit.code == code)
    )
    if existing.scalar_one_or_none():
        raise AppException(code="unit_code_exists", message="Unit code already exists", http_status=409)

    unit = Unit(**data, tenant_id=tenant_id)
    session.add(unit)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_units_tenant_code" in message or "units_tenant_id_code" in message:
            raise AppException(
                code="unit_code_exists",
                message="Unit code already exists",
                http_status=409,
            ) from exc
        raise
    await session.refresh(unit)
    return unit


async def update_unit(
    session: AsyncSession, tenant_id: UUID, unit_id: UUID, payload: Any
) -> Unit | None:
    unit = await get_unit(session, tenant_id, unit_id)
    if not unit:
        return None
    data = _to_dict(payload, exclude_unset=True)
    allowed_fields = {"code", "name", "is_base"}
    changes = {field: value for field, value in data.items() if field in allowed_fields}
    if not changes:
        return unit

    if "code" in changes:
        code = (changes.get("code") or "").strip()
        if not code:
            raise AppException(code="unit_code_required", message="Unit code is required", http_status=422)
        existing = await session.execute(
            select(Unit.id).where(
                Unit.tenant_id == tenant_id,
                Unit.code == code,
                Unit.id != unit_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(code="unit_code_exists", message="Unit code already exists", http_status=409)
        changes["code"] = code

    if "name" in changes:
        name = (changes.get("name") or "").strip()
        if not name:
            raise AppException(code="unit_name_required", message="Unit name is required", http_status=422)
        changes["name"] = name

    for field, value in changes.items():
        setattr(unit, field, value)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_units_tenant_code" in message or "units_tenant_id_code" in message:
            raise AppException(
                code="unit_code_exists",
                message="Unit code already exists",
                http_status=409,
            ) from exc
        raise
    await session.refresh(unit)
    return unit


__all__ = [
    "list_units",
    "get_unit",
    "create_unit",
    "update_unit",
]
