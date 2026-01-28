from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.pagination import PaginationParams, paginate_query
from app.models.product import Product, ProductStatus
from app.models.stock_move import StockMove, StockMoveDirection, StockMoveSourceType
from app.models.unit import InventoryUnit
from app.services.period_guard import PeriodGuard


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _quantize_qty(value: Decimal | str | int | float | None) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.000001"))


@asynccontextmanager
async def _transaction_scope(session: AsyncSession):
    if session.in_transaction():
        await session.rollback()
    async with session.begin():
        yield


async def _get_product(
    session: AsyncSession,
    tenant_id: UUID,
    product_id: UUID,
    *,
    require_active: bool = True,
) -> Product:
    result = await session.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise AppException(code="product_not_found", message="Product not found", http_status=404)
    if require_active and (
        getattr(product, "status", None) == ProductStatus.INACTIVE
        or getattr(product, "is_active", True) is False
    ):
        raise AppException(code="product_inactive", message="Product is inactive", http_status=409)
    return product


async def _get_unit(session: AsyncSession, tenant_id: UUID, unit_id: UUID) -> InventoryUnit:
    result = await session.execute(
        select(InventoryUnit).where(
            InventoryUnit.id == unit_id, InventoryUnit.tenant_id == tenant_id
        )
    )
    unit = result.scalar_one_or_none()
    if not unit:
        raise AppException(code="inventory_unit_not_found", message="Inventory unit not found", http_status=404)
    return unit


async def _get_balance_for_update(
    session: AsyncSession, tenant_id: UUID, product_id: UUID
) -> Decimal:
    lock_stmt = (
        select(Product.id)
        .where(Product.id == product_id, Product.tenant_id == tenant_id)
        .with_for_update()
    )
    await session.execute(lock_stmt)
    result = await session.execute(
        select(func.coalesce(func.sum(StockMove.base_quantity), 0)).where(
            StockMove.tenant_id == tenant_id, StockMove.product_id == product_id
        )
    )
    return _quantize_qty(result.scalar_one() or 0)


def _normalize_direction(value: StockMoveDirection | str | None) -> StockMoveDirection:
    if value is None:
        raise AppException(
            code="stock_move_direction_required",
            message="Move direction is required",
            http_status=422,
        )
    if isinstance(value, StockMoveDirection):
        return value
    try:
        return StockMoveDirection(str(value))
    except Exception as exc:
        raise AppException(
            code="stock_move_direction_invalid",
            message="Move direction is invalid",
            http_status=422,
        ) from exc


def _normalize_source_type(value: StockMoveSourceType | str | None) -> StockMoveSourceType:
    if value is None:
        raise AppException(
            code="stock_move_source_required",
            message="Source type is required",
            http_status=422,
        )
    if isinstance(value, StockMoveSourceType):
        return value
    try:
        return StockMoveSourceType(str(value))
    except Exception as exc:
        raise AppException(
            code="stock_move_source_invalid",
            message="Source type is invalid",
            http_status=422,
        ) from exc


async def list_ledger(
    session: AsyncSession,
    tenant_id: UUID,
    params: PaginationParams,
    *,
    product_id: UUID | None = None,
) -> tuple[Sequence[StockMove], int]:
    statement = select(StockMove).where(StockMove.tenant_id == tenant_id)
    if product_id:
        await _get_product(session, tenant_id, product_id, require_active=False)
        statement = statement.where(StockMove.product_id == product_id)
    statement = statement.order_by(StockMove.posted_at.desc(), StockMove.created_at.desc())
    return await paginate_query(session, statement, params)


async def get_balance(session: AsyncSession, tenant_id: UUID, product_id: UUID) -> Decimal:
    await _get_product(session, tenant_id, product_id, require_active=False)
    result = await session.execute(
        select(func.coalesce(func.sum(StockMove.base_quantity), 0)).where(
            StockMove.tenant_id == tenant_id, StockMove.product_id == product_id
        )
    )
    return _quantize_qty(result.scalar_one() or 0)


async def find_moves_by_source(
    session: AsyncSession,
    tenant_id: UUID,
    source_type: StockMoveSourceType,
    source_id: UUID,
) -> list[StockMove]:
    result = await session.execute(
        select(StockMove)
        .where(
            StockMove.tenant_id == tenant_id,
            StockMove.source_type == source_type,
            StockMove.source_id == source_id,
        )
        .order_by(StockMove.created_at.asc())
    )
    return list(result.scalars().all())


async def create_stock_move(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
    *,
    commit: bool = True,
) -> StockMove:
    data = _to_dict(payload)
    product_id = data.get("product_id")
    if not product_id:
        raise AppException(code="product_id_required", message="Product is required", http_status=422)
    product = await _get_product(session, tenant_id, product_id)

    quantity = _quantize_qty(data.get("quantity"))
    if quantity <= 0:
        raise AppException(
            code="stock_quantity_invalid",
            message="Quantity must be greater than zero",
            http_status=422,
        )

    direction = _normalize_direction(data.get("direction"))
    source_type = _normalize_source_type(data.get("source_type"))
    source_id = data.get("source_id")
    if not source_id:
        raise AppException(
            code="stock_move_source_required",
            message="Source id is required",
            http_status=422,
        )

    unit_id = data.get("unit_id") or product.base_unit_id
    if not unit_id:
        raise AppException(
            code="product_base_unit_required",
            message="Product base unit is required for inventory posting",
            http_status=422,
        )
    unit = await _get_unit(session, tenant_id, unit_id)
    ratio = _quantize_qty(unit.ratio_to_base or 1)
    if ratio <= 0:
        raise AppException(
            code="inventory_unit_ratio_invalid",
            message="ratio_to_base must be greater than zero",
            http_status=422,
        )
    base_quantity_abs = _quantize_qty(quantity * ratio)
    if base_quantity_abs <= 0:
        raise AppException(
            code="stock_quantity_invalid",
            message="Base quantity must be greater than zero",
            http_status=422,
        )

    signed_quantity = quantity if direction == StockMoveDirection.IN else -quantity
    signed_base_quantity = base_quantity_abs if direction == StockMoveDirection.IN else -base_quantity_abs

    posted_at = data.get("posted_at")
    if posted_at is None:
        posted_at = datetime.now(UTC)
    elif isinstance(posted_at, date) and not isinstance(posted_at, datetime):
        posted_at = datetime.combine(posted_at, datetime.min.time(), tzinfo=UTC)

    guard = PeriodGuard(session=session)
    await guard.assert_open(tenant_id=tenant_id, entry_date=posted_at.date())

    async def _apply_move() -> StockMove:
        current_balance = await _get_balance_for_update(session, tenant_id, product_id)
        if direction == StockMoveDirection.OUT:
            projected = _quantize_qty(current_balance + signed_base_quantity)
            if projected < 0:
                raise AppException(
                    code="insufficient_stock",
                    message="Insufficient stock for this movement",
                    http_status=409,
                )
        reference_type = {
            StockMoveSourceType.SALE: "sales_invoice",
            StockMoveSourceType.PURCHASE: "purchase_invoice",
            StockMoveSourceType.REVERSAL: "stock_reversal",
        }.get(source_type, str(source_type.value).lower())
        posting_entry_id = data.get("posting_journal_entry_id") or data.get("posted_journal_entry_id")
        move = StockMove(
            tenant_id=tenant_id,
            product_id=product_id,
            quantity=signed_quantity,
            unit_id=unit_id,
            base_quantity=signed_base_quantity,
            direction=direction,
            source_type=source_type,
            source_id=source_id,
            posting_journal_entry_id=posting_entry_id,
            posted_at=posted_at,
            reversed_stock_move_id=data.get("reversed_stock_move_id"),
            move_date=posted_at.date(),
            quantity_base=abs(base_quantity_abs),
            quantity_original=quantity,
            reference_type=reference_type,
            reference_id=source_id,
        )
        session.add(move)
        return move

    if commit:
        async with _transaction_scope(session):
            move = await _apply_move()
    else:
        move = await _apply_move()
        await session.flush()

    await session.refresh(move)
    return move


async def create_reversal_moves(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    source_id: UUID,
    original_moves: Sequence[StockMove],
    posting_journal_entry_id: UUID | None,
    posted_at: datetime,
) -> list[StockMove]:
    if not original_moves:
        return []
    reversal_moves = await find_moves_by_source(
        session, tenant_id, StockMoveSourceType.REVERSAL, source_id
    )
    reversed_ids = {move.reversed_stock_move_id for move in reversal_moves if move.reversed_stock_move_id}
    created: list[StockMove] = []
    for move in original_moves:
        if move.id in reversed_ids:
            continue
        quantity_abs = _quantize_qty(abs(move.quantity))
        direction = StockMoveDirection.IN if move.direction == StockMoveDirection.OUT else StockMoveDirection.OUT
        created.append(
            await create_stock_move(
                session,
                tenant_id,
                {
                    "product_id": move.product_id,
                    "quantity": quantity_abs,
                    "unit_id": move.unit_id,
                    "direction": direction,
                    "source_type": StockMoveSourceType.REVERSAL,
                    "source_id": source_id,
                    "posting_journal_entry_id": posting_journal_entry_id,
                    "posted_at": posted_at,
                    "reversed_stock_move_id": move.id,
                },
                commit=False,
            )
        )
    return created


__all__ = [
    "list_ledger",
    "get_balance",
    "find_moves_by_source",
    "create_stock_move",
    "create_reversal_moves",
]
