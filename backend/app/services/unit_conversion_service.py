from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.pagination import PaginationParams, paginate_query
from app.models.unit import Unit
from app.models.unit_conversion import UnitConversion


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def _get_unit(session: AsyncSession, tenant_id: UUID, unit_id: UUID) -> Unit:
    result = await session.execute(
        select(Unit).where(Unit.id == unit_id, Unit.tenant_id == tenant_id)
    )
    unit = result.scalar_one_or_none()
    if not unit:
        raise AppException(code="unit_not_found", message="Unit not found", http_status=404)
    return unit


def _normalize_multiplier(value: Decimal | str | int | float | None) -> Decimal:
    multiplier = Decimal(str(value or 0))
    if multiplier <= 0:
        raise AppException(
            code="unit_multiplier_invalid",
            message="Multiplier must be greater than zero",
            http_status=422,
        )
    return multiplier


async def list_conversions(
    session: AsyncSession,
    tenant_id: UUID,
    params: PaginationParams,
    *,
    from_unit_id: UUID | None = None,
    to_unit_id: UUID | None = None,
) -> tuple[list[UnitConversion], int]:
    statement = select(UnitConversion).where(UnitConversion.tenant_id == tenant_id)
    if from_unit_id:
        statement = statement.where(UnitConversion.from_unit_id == from_unit_id)
    if to_unit_id:
        statement = statement.where(UnitConversion.to_unit_id == to_unit_id)
    statement = statement.order_by(UnitConversion.created_at.desc())
    return await paginate_query(session, statement, params)


async def get_conversion(
    session: AsyncSession, tenant_id: UUID, conversion_id: UUID
) -> UnitConversion | None:
    result = await session.execute(
        select(UnitConversion).where(
            UnitConversion.id == conversion_id, UnitConversion.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()


async def create_conversion(session: AsyncSession, tenant_id: UUID, payload: Any) -> UnitConversion:
    data = _to_dict(payload)
    from_unit_id = data.get("from_unit_id")
    to_unit_id = data.get("to_unit_id")
    if not from_unit_id or not to_unit_id:
        raise AppException(
            code="unit_conversion_units_required",
            message="Both from_unit_id and to_unit_id are required",
            http_status=422,
        )
    if from_unit_id == to_unit_id:
        raise AppException(
            code="unit_conversion_invalid",
            message="from_unit_id and to_unit_id must be different",
            http_status=422,
        )

    await _get_unit(session, tenant_id, from_unit_id)
    await _get_unit(session, tenant_id, to_unit_id)

    multiplier = _normalize_multiplier(data.get("multiplier"))
    data["multiplier"] = multiplier

    existing = await session.execute(
        select(UnitConversion.id).where(
            UnitConversion.tenant_id == tenant_id,
            UnitConversion.from_unit_id == from_unit_id,
            UnitConversion.to_unit_id == to_unit_id,
        )
    )
    if existing.scalar_one_or_none():
        raise AppException(
            code="unit_conversion_exists",
            message="Unit conversion already exists",
            http_status=409,
        )

    conversion = UnitConversion(**data, tenant_id=tenant_id)
    session.add(conversion)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_unit_conversions_tenant_from_to" in message:
            raise AppException(
                code="unit_conversion_exists",
                message="Unit conversion already exists",
                http_status=409,
            ) from exc
        raise
    await session.refresh(conversion)
    return conversion


async def update_conversion(
    session: AsyncSession,
    tenant_id: UUID,
    conversion_id: UUID,
    payload: Any,
) -> UnitConversion | None:
    conversion = await get_conversion(session, tenant_id, conversion_id)
    if not conversion:
        return None
    data = _to_dict(payload, exclude_unset=True)
    if "multiplier" not in data:
        return conversion
    conversion.multiplier = _normalize_multiplier(data.get("multiplier"))
    await session.commit()
    await session.refresh(conversion)
    return conversion


async def delete_conversion(session: AsyncSession, tenant_id: UUID, conversion_id: UUID) -> bool:
    result = await session.execute(
        delete(UnitConversion).where(
            UnitConversion.id == conversion_id, UnitConversion.tenant_id == tenant_id
        )
    )
    await session.commit()
    return result.rowcount > 0


async def resolve_multiplier(
    session: AsyncSession,
    tenant_id: UUID,
    from_unit_id: UUID,
    to_unit_id: UUID,
) -> Decimal:
    if from_unit_id == to_unit_id:
        return Decimal("1")
    result = await session.execute(
        select(UnitConversion).where(
            UnitConversion.tenant_id == tenant_id,
            UnitConversion.from_unit_id == from_unit_id,
            UnitConversion.to_unit_id == to_unit_id,
        )
    )
    conversion = result.scalar_one_or_none()
    if not conversion:
        raise AppException(
            code="unit_conversion_not_found",
            message="Unit conversion not found",
            http_status=404,
        )
    return Decimal(str(conversion.multiplier))


__all__ = [
    "list_conversions",
    "get_conversion",
    "create_conversion",
    "update_conversion",
    "delete_conversion",
    "resolve_multiplier",
]
