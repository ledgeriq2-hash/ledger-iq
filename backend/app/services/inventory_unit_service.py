from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.pagination import PaginationParams, paginate_query
from app.models.unit import InventoryUnit


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _normalize_ratio(value: Decimal | str | int | float | None) -> Decimal:
    ratio = Decimal(str(value or 0)).quantize(Decimal("0.000001"))
    if ratio <= 0:
        raise AppException(
            code="inventory_unit_ratio_invalid",
            message="ratio_to_base must be greater than zero",
            http_status=422,
        )
    return ratio


async def list_units(
    session: AsyncSession,
    tenant_id: UUID,
    params: PaginationParams,
) -> tuple[list[InventoryUnit], int]:
    statement = select(InventoryUnit).where(InventoryUnit.tenant_id == tenant_id).order_by(
        InventoryUnit.code.asc()
    )
    return await paginate_query(session, statement, params)


async def get_unit(
    session: AsyncSession, tenant_id: UUID, unit_id: UUID
) -> InventoryUnit | None:
    result = await session.execute(
        select(InventoryUnit).where(InventoryUnit.id == unit_id, InventoryUnit.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_unit(
    session: AsyncSession, tenant_id: UUID, payload: Any
) -> InventoryUnit:
    data = _to_dict(payload)
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    if not code:
        raise AppException(
            code="inventory_unit_code_required",
            message="Inventory unit code is required",
            http_status=422,
        )
    if not name:
        raise AppException(
            code="inventory_unit_name_required",
            message="Inventory unit name is required",
            http_status=422,
        )

    ratio_to_base = _normalize_ratio(data.get("ratio_to_base") or 1)
    is_base = ratio_to_base == Decimal("1.000000")
    if data.get("is_base") is True and not is_base:
        raise AppException(
            code="inventory_unit_ratio_mismatch",
            message="ratio_to_base must be 1 for base units",
            http_status=422,
        )

    existing = await session.execute(
        select(InventoryUnit.id).where(
            InventoryUnit.tenant_id == tenant_id,
            InventoryUnit.code == code,
        )
    )
    if existing.scalar_one_or_none():
        raise AppException(
            code="inventory_unit_code_exists",
            message="Inventory unit code already exists",
            http_status=409,
        )

    unit = InventoryUnit(
        tenant_id=tenant_id,
        code=code,
        name=name,
        ratio_to_base=ratio_to_base,
        is_base=is_base,
    )
    session.add(unit)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_units_tenant_code" in message or "inventory_units_tenant_id_code" in message:
            raise AppException(
                code="inventory_unit_code_exists",
                message="Inventory unit code already exists",
                http_status=409,
            ) from exc
        raise
    await session.refresh(unit)
    return unit


__all__ = ["list_units", "get_unit", "create_unit"]
