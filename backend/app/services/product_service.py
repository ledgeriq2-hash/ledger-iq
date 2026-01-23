from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.pagination import PaginationParams, paginate_query
from app.models.product import Product, ProductStatus
from app.models.unit import Unit


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
    if "metadata" in data and "metadata_json" not in data:
        data["metadata_json"] = data.pop("metadata")

    sku = (data.get("sku") or "").strip()
    name = (data.get("name") or "").strip()
    if not sku:
        raise AppException(code="product_sku_required", message="Product SKU is required", http_status=422)
    if not name:
        raise AppException(code="product_name_required", message="Product name is required", http_status=422)
    data["sku"] = sku
    data["name"] = name

    status = data.get("status")
    if status is not None:
        try:
            data["status"] = ProductStatus(status)
        except Exception as exc:
            raise AppException(
                code="product_status_invalid",
                message="Product status is invalid",
                http_status=422,
            ) from exc

    base_unit_id = data.get("base_unit_id")
    if not base_unit_id:
        raise AppException(code="product_base_unit_required", message="Base unit is required", http_status=422)
    await _get_unit(session, tenant_id, base_unit_id)

    existing = await session.execute(
        select(Product.id).where(Product.tenant_id == tenant_id, Product.sku == sku)
    )
    if existing.scalar_one_or_none():
        raise AppException(code="product_sku_exists", message="Product SKU already exists", http_status=409)

    product = Product(**data, tenant_id=tenant_id)
    session.add(product)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_products_tenant_sku" in message or "products_tenant_id_sku" in message:
            raise AppException(
                code="product_sku_exists",
                message="Product SKU already exists",
                http_status=409,
            ) from exc
        raise
    await session.refresh(product)
    return product


async def update_product(
    session: AsyncSession, tenant_id: UUID, product_id: UUID, payload: Any
) -> Product | None:
    product = await get_product(session, tenant_id, product_id)
    if not product:
        return None
    data = _to_dict(payload, exclude_unset=True)
    if "metadata" in data and "metadata_json" not in data:
        data["metadata_json"] = data.pop("metadata")

    allowed_fields = {"sku", "name", "status", "base_unit_id", "notes", "metadata_json"}
    changes = {field: value for field, value in data.items() if field in allowed_fields}
    if not changes:
        return product

    if "sku" in changes:
        sku = (changes.get("sku") or "").strip()
        if not sku:
            raise AppException(code="product_sku_required", message="Product SKU is required", http_status=422)
        existing = await session.execute(
            select(Product.id).where(
                Product.tenant_id == tenant_id,
                Product.sku == sku,
                Product.id != product_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(code="product_sku_exists", message="Product SKU already exists", http_status=409)
        changes["sku"] = sku

    if "name" in changes:
        name = (changes.get("name") or "").strip()
        if not name:
            raise AppException(code="product_name_required", message="Product name is required", http_status=422)
        changes["name"] = name

    if "status" in changes and changes["status"] is not None:
        try:
            changes["status"] = ProductStatus(changes["status"])
        except Exception as exc:
            raise AppException(
                code="product_status_invalid",
                message="Product status is invalid",
                http_status=422,
            ) from exc

    if "base_unit_id" in changes and changes["base_unit_id"] is not None:
        await _get_unit(session, tenant_id, changes["base_unit_id"])

    for field, value in changes.items():
        setattr(product, field, value)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_products_tenant_sku" in message or "products_tenant_id_sku" in message:
            raise AppException(
                code="product_sku_exists",
                message="Product SKU already exists",
                http_status=409,
            ) from exc
        raise
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
