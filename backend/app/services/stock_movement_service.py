from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AppException
from app.models.product import Product
from app.models.stock_movement import MovementType, ReferenceType, StockMovement
from app.schemas.stock_movement import InventorySummaryItem

settings = get_settings()


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def _get_product(session: AsyncSession, tenant_id: UUID, product_id: UUID) -> Product | None:
    result = await session.execute(select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id))
    return result.scalar_one_or_none()


def _apply_quantity(current: Decimal, movement_type: MovementType, quantity: Decimal) -> Decimal:
    if movement_type == MovementType.IN:
        return current + quantity
    if movement_type == MovementType.OUT:
        return current - quantity
    if movement_type == MovementType.ADJUST:
        return quantity
    return current


async def _validate_stock_balance(new_quantity: Decimal) -> None:
    if new_quantity < 0 and not settings.allow_negative_stock:
        raise AppException(code="stock_negative", message="Stock cannot go negative")


async def _apply_stock_change(product: Product, movement_type: MovementType, quantity: Decimal) -> None:
    new_qty = _apply_quantity(Decimal(str(product.stock_quantity or 0)), movement_type, quantity)
    await _validate_stock_balance(new_qty)
    product.stock_quantity = new_qty


async def list_movements(
    session: AsyncSession,
    tenant_id: UUID,
    page: int = 1,
    page_size: int = 50,
    product_id: UUID | None = None,
    movement_type: MovementType | None = None,
    reference_type: ReferenceType | None = None,
) -> tuple[Sequence[StockMovement], int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 200))

    query = select(StockMovement).where(StockMovement.tenant_id == tenant_id)
    if product_id:
        query = query.where(StockMovement.product_id == product_id)
    if movement_type:
        query = query.where(StockMovement.movement_type == movement_type)
    if reference_type:
        query = query.where(StockMovement.reference_type == reference_type)

    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = int(total_result.scalar_one() or 0)

    result = await session.execute(
        query.order_by(StockMovement.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return result.scalars().all(), total


async def create_movement(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
    *,
    commit: bool = True,
) -> StockMovement:
    data = _to_dict(payload)
    quantity = Decimal(str(data["quantity"]))
    movement_type = MovementType(data["movement_type"])
    product = await _get_product(session, tenant_id, data["product_id"])
    if not product:
        raise AppException(code="product_not_found", message="Product not found", http_status=404)

    skip_stock = bool(getattr(product, "is_service", False))
    if not skip_stock:
        await _apply_stock_change(product, movement_type, quantity)

    ref_type = ReferenceType(data["reference_type"]) if data.get("reference_type") else None

    movement = StockMovement(
        product_id=product.id,
        quantity=quantity,
        movement_type=movement_type,
        reference_type=ref_type,
        reference_id=data.get("reference_id"),
        tenant_id=tenant_id,
    )
    session.add(movement)
    if commit:
        await session.commit()
        await session.refresh(movement)
    else:
        await session.flush()
    return movement


async def get_movement(session: AsyncSession, tenant_id: UUID, movement_id: UUID) -> StockMovement | None:
    result = await session.execute(
        select(StockMovement).where(StockMovement.id == movement_id, StockMovement.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def update_movement(
    session: AsyncSession,
    tenant_id: UUID,
    movement_id: UUID,
    payload: Any,
) -> StockMovement | None:
    movement = await get_movement(session, tenant_id, movement_id)
    if not movement:
        return None
    raise AppException(code="movement_immutable", message="Stock movements cannot be edited; create a new movement instead")


async def delete_movement(session: AsyncSession, tenant_id: UUID, movement_id: UUID) -> bool:
    movement = await get_movement(session, tenant_id, movement_id)
    if not movement:
        return False
    product = await _get_product(session, tenant_id, movement.product_id)
    if product:
        # revert
        current_qty = Decimal(str(product.stock_quantity or 0))
        if movement.movement_type == MovementType.IN:
            current_qty -= movement.quantity
        elif movement.movement_type == MovementType.OUT:
            current_qty += movement.quantity
        # ADJUST is not reverted to avoid losing prior state
        await _validate_stock_balance(current_qty)
        product.stock_quantity = current_qty
    await session.delete(movement)
    await session.commit()
    return True


async def summarize_inventory(session: AsyncSession, tenant_id: UUID) -> tuple[list[InventorySummaryItem], Decimal]:
    result = await session.execute(select(Product).where(Product.tenant_id == tenant_id))
    items: list[InventorySummaryItem] = []
    total_value = Decimal("0")
    for product in result.scalars().all():
        stock_qty = Decimal(str(product.stock_quantity or 0))
        cost = Decimal(str(product.cost_price or 0))
        valuation = (stock_qty * cost).quantize(Decimal("0.01"))
        total_value += valuation
        items.append(
            InventorySummaryItem(
                product_id=product.id,
                product_name=product.name,
                sku=product.sku,
                stock_quantity=stock_qty,
                cost_price=cost,
                valuation=valuation,
            )
        )
    return items, total_value


async def apply_invoice_movements(session: AsyncSession, tenant_id: UUID, invoice, *, commit: bool = True) -> None:
    """
    Create OUT movements for invoice items with products.
    """
    if not getattr(invoice, "items", None):
        return
    for item in invoice.items:
        if not item.product_id:
            continue
        await create_movement(
            session,
            tenant_id,
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "movement_type": MovementType.OUT,
                "reference_type": ReferenceType.INVOICE,
                "reference_id": invoice.id,
            },
            commit=False,
        )
    if commit:
        await session.commit()
    else:
        await session.flush()


__all__ = [
    "list_movements",
    "create_movement",
    "get_movement",
    "update_movement",
    "delete_movement",
    "summarize_inventory",
    "apply_invoice_movements",
]
