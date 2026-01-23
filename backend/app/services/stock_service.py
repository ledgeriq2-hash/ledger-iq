from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.pagination import PaginationParams, paginate_query
from app.models.product import Product, ProductStatus
from app.models.stock_balance import StockBalance
from app.models.stock_move import StockMove, StockMoveDirection
from app.models.unit import Unit
from app.services.period_guard import PeriodGuard
from app.services.unit_conversion_service import resolve_multiplier


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _quantize(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


@asynccontextmanager
async def _transaction_scope(session: AsyncSession):
    if session.in_transaction():
        await session.rollback()
    async with session.begin():
        yield


async def _get_product(session: AsyncSession, tenant_id: UUID, product_id: UUID) -> Product:
    result = await session.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise AppException(code="product_not_found", message="Product not found", http_status=404)
    if getattr(product, "status", None) == ProductStatus.INACTIVE:
        raise AppException(code="product_inactive", message="Product is inactive", http_status=409)
    return product


async def _get_unit(session: AsyncSession, tenant_id: UUID, unit_id: UUID) -> Unit:
    result = await session.execute(
        select(Unit).where(Unit.id == unit_id, Unit.tenant_id == tenant_id)
    )
    unit = result.scalar_one_or_none()
    if not unit:
        raise AppException(code="unit_not_found", message="Unit not found", http_status=404)
    return unit


async def _get_balance_for_update(
    session: AsyncSession, tenant_id: UUID, product_id: UUID
) -> StockBalance | None:
    stmt = (
        select(StockBalance)
        .where(StockBalance.tenant_id == tenant_id, StockBalance.product_id == product_id)
        .with_for_update()
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_moves(
    session: AsyncSession,
    tenant_id: UUID,
    params: PaginationParams,
    *,
    product_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
) -> tuple[Sequence[StockMove], int]:
    statement = select(StockMove).where(StockMove.tenant_id == tenant_id)
    if product_id:
        statement = statement.where(StockMove.product_id == product_id)
    if date_from:
        statement = statement.where(StockMove.move_date >= date_from)
    if date_to:
        statement = statement.where(StockMove.move_date <= date_to)
    if reference_type:
        statement = statement.where(StockMove.reference_type == reference_type)
    if reference_id:
        statement = statement.where(StockMove.reference_id == reference_id)
    statement = statement.order_by(StockMove.move_date.desc(), StockMove.created_at.desc())
    return await paginate_query(session, statement, params)


async def get_balance(
    session: AsyncSession, tenant_id: UUID, product_id: UUID
) -> StockBalance:
    result = await session.execute(
        select(StockBalance).where(
            StockBalance.tenant_id == tenant_id, StockBalance.product_id == product_id
        )
    )
    balance = result.scalar_one_or_none()
    if balance:
        return balance
    now = datetime.now(UTC)
    return StockBalance(
        tenant_id=tenant_id,
        product_id=product_id,
        on_hand_qty_base=Decimal("0.00"),
        created_at=now,
        updated_at=now,
    )


async def record_move(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
) -> tuple[StockMove, StockBalance]:
    data = _to_dict(payload)
    product_id = data.get("product_id")
    if not product_id:
        raise AppException(code="product_id_required", message="Product is required", http_status=422)
    product = await _get_product(session, tenant_id, product_id)

    move_date = data.get("move_date")
    if not move_date:
        raise AppException(code="move_date_required", message="Move date is required", http_status=422)

    direction_value = data.get("direction")
    if direction_value is None:
        raise AppException(
            code="stock_move_direction_required",
            message="Move direction is required",
            http_status=422,
        )
    try:
        direction = (
            direction_value
            if isinstance(direction_value, StockMoveDirection)
            else StockMoveDirection(str(direction_value))
        )
    except Exception as exc:
        raise AppException(
            code="stock_move_direction_invalid",
            message="Move direction is invalid",
            http_status=422,
        ) from exc

    reference_type = (data.get("reference_type") or "").strip()
    reference_id = data.get("reference_id")
    if not reference_type or not reference_id:
        raise AppException(
            code="stock_move_reference_required",
            message="Reference type and id are required",
            http_status=422,
        )

    unit_id = data.get("unit_id")
    quantity_original = data.get("quantity_original")
    if quantity_original is not None:
        quantity_original = _quantize(quantity_original)
        if quantity_original <= 0:
            raise AppException(
                code="stock_quantity_invalid",
                message="Original quantity must be greater than zero",
                http_status=422,
            )

    if unit_id:
        await _get_unit(session, tenant_id, unit_id)

    quantity_base = data.get("quantity_base")
    if quantity_base is not None:
        quantity_base = _quantize(quantity_base)
        if quantity_base <= 0:
            raise AppException(
                code="stock_quantity_invalid",
                message="Base quantity must be greater than zero",
                http_status=422,
            )

    if quantity_base is None:
        if quantity_original is None or not unit_id:
            raise AppException(
                code="stock_quantity_required",
                message="quantity_base is required when no conversion data is provided",
                http_status=422,
            )
        base_unit_id = product.base_unit_id
        if not base_unit_id:
            raise AppException(
                code="product_base_unit_required",
                message="Product base unit is required for conversion",
                http_status=422,
            )
        if unit_id == base_unit_id:
            quantity_base = quantity_original
        else:
            multiplier = await resolve_multiplier(session, tenant_id, unit_id, base_unit_id)
            quantity_base = _quantize(quantity_original * multiplier)

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=move_date)

    async with _transaction_scope(session):
        balance = await _get_balance_for_update(session, tenant_id, product_id)
        if not balance:
            balance = StockBalance(
                tenant_id=tenant_id,
                product_id=product_id,
                on_hand_qty_base=Decimal("0.00"),
            )
            session.add(balance)
            await session.flush()

        current_qty = _quantize(balance.on_hand_qty_base)
        if direction == StockMoveDirection.OUT:
            new_qty = current_qty - quantity_base
            if new_qty < 0:
                raise AppException(
                    code="insufficient_stock",
                    message="Insufficient stock for this movement",
                    http_status=409,
                )
        else:
            new_qty = current_qty + quantity_base

        move = StockMove(
            tenant_id=tenant_id,
            product_id=product_id,
            move_date=move_date,
            direction=direction,
            quantity_base=quantity_base,
            unit_id=unit_id,
            quantity_original=quantity_original,
            reference_type=reference_type,
            reference_id=reference_id,
            posted_journal_entry_id=data.get("posted_journal_entry_id"),
        )
        session.add(move)
        balance.on_hand_qty_base = new_qty

    await session.refresh(move)
    await session.refresh(balance)
    return move, balance


__all__ = [
    "list_moves",
    "get_balance",
    "record_move",
]
