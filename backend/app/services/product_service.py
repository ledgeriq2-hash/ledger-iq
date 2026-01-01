from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams, paginate_query
from app.models.product import Product


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_products(
    session: AsyncSession, tenant_id: UUID, params: PaginationParams
) -> tuple[list[Product], int]:
    statement = select(Product).where(Product.tenant_id == tenant_id)
    return await paginate_query(session, statement, params)


async def get_product(session: AsyncSession, tenant_id: UUID, product_id: UUID) -> Product | None:
    result = await session.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_product(session: AsyncSession, tenant_id: UUID, payload: Any) -> Product:
    data = _to_dict(payload)
    product = Product(**data, tenant_id=tenant_id)
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


async def update_product(
    session: AsyncSession, tenant_id: UUID, product_id: UUID, payload: Any
) -> Product | None:
    product = await get_product(session, tenant_id, product_id)
    if not product:
        return None
    data = _to_dict(payload, exclude_unset=True)
    for field, value in data.items():
        if field in {"id", "tenant_id"}:
            continue
        setattr(product, field, value)
    await session.commit()
    await session.refresh(product)
    return product


async def delete_product(session: AsyncSession, tenant_id: UUID, product_id: UUID) -> bool:
    result = await session.execute(
        delete(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    await session.commit()
    return result.rowcount > 0


__all__ = [
    "list_products",
    "get_product",
    "create_product",
    "update_product",
    "delete_product",
]
