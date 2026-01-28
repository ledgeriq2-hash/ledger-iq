from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.pagination import PaginationParams, paginate_query
from app.models.product import Product, ProductStatus
from app.models.unit import InventoryUnit


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def _get_unit(session: AsyncSession, tenant_id: UUID, unit_id: UUID) -> InventoryUnit:
    result = await session.execute(
        select(InventoryUnit).where(
            InventoryUnit.id == unit_id, InventoryUnit.tenant_id == tenant_id
        )
    )
    unit = result.scalar_one_or_none()
    if not unit:
        raise AppException(code="unit_not_found", message="Unit not found", http_status=404)
    return unit


async def _next_product_code(session: AsyncSession, tenant_id: UUID) -> str:
    prefix = "PROD-"
    pattern = f"^{prefix}\\d{{6}}$"
    result = await session.execute(
        select(func.max(Product.code)).where(
            Product.tenant_id == tenant_id,
            Product.code.op("~")(pattern),
        )
    )
    max_code = result.scalar_one_or_none()
    next_value = 1
    if max_code:
        try:
            next_value = int(str(max_code).replace(prefix, "")) + 1
        except ValueError:
            next_value = 1
    return f"{prefix}{next_value:06d}"


async def _ensure_product_code(session: AsyncSession, tenant_id: UUID, code: str | None) -> str:
    cleaned = (code or "").strip()
    if cleaned:
        return cleaned
    for _ in range(5):
        candidate = await _next_product_code(session, tenant_id)
        exists = await session.execute(
            select(Product.id).where(Product.tenant_id == tenant_id, Product.code == candidate)
        )
        if exists.scalar_one_or_none():
            continue
        return candidate
    raise AppException(
        code="product_code_conflict",
        message="Unable to generate unique product code",
        http_status=409,
    )


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

    code = (data.get("code") or "").strip()
    sku = (data.get("sku") or "").strip()
    name = (data.get("name") or "").strip()
    if not name:
        raise AppException(code="product_name_required", message="Product name is required", http_status=422)
    data["name"] = name
    data["code"] = await _ensure_product_code(session, tenant_id, code)
    data["sku"] = sku or None

    status = data.get("status")
    is_active = data.get("is_active")
    if status is not None:
        try:
            data["status"] = ProductStatus(status)
        except Exception as exc:
            raise AppException(
                code="product_status_invalid",
                message="Product status is invalid",
                http_status=422,
            ) from exc
        expected_active = data["status"] == ProductStatus.ACTIVE
        if is_active is not None and bool(is_active) != expected_active:
            raise AppException(
                code="product_status_mismatch",
                message="status and is_active are inconsistent",
                http_status=422,
            )
        data["is_active"] = expected_active
    elif is_active is not None:
        data["is_active"] = bool(is_active)
        data["status"] = ProductStatus.ACTIVE if data["is_active"] else ProductStatus.INACTIVE
    else:
        data["status"] = ProductStatus.ACTIVE
        data["is_active"] = True

    base_unit_id = data.get("base_unit_id")
    if not base_unit_id:
        raise AppException(code="product_base_unit_required", message="Base unit is required", http_status=422)
    await _get_unit(session, tenant_id, base_unit_id)

    if data.get("code"):
        existing = await session.execute(
            select(Product.id).where(Product.tenant_id == tenant_id, Product.code == data["code"])
        )
        if existing.scalar_one_or_none():
            raise AppException(code="product_code_exists", message="Product code already exists", http_status=409)

    if data.get("sku"):
        existing = await session.execute(
            select(Product.id).where(Product.tenant_id == tenant_id, Product.sku == data["sku"])
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
        if "uq_products_tenant_code" in message:
            raise AppException(
                code="product_code_exists",
                message="Product code already exists",
                http_status=409,
            ) from exc
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

    allowed_fields = {
        "code",
        "sku",
        "name",
        "status",
        "is_active",
        "base_unit_id",
        "notes",
        "metadata_json",
    }
    changes = {field: value for field, value in data.items() if field in allowed_fields}
    if not changes:
        return product

    if "code" in changes:
        code = (changes.get("code") or "").strip()
        if not code:
            raise AppException(code="product_code_required", message="Product code is required", http_status=422)
        existing = await session.execute(
            select(Product.id).where(
                Product.tenant_id == tenant_id,
                Product.code == code,
                Product.id != product_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(code="product_code_exists", message="Product code already exists", http_status=409)
        changes["code"] = code

    if "sku" in changes:
        sku = (changes.get("sku") or "").strip()
        if not sku:
            changes["sku"] = None
        else:
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
        expected_active = changes["status"] == ProductStatus.ACTIVE
        if "is_active" in changes and changes["is_active"] is not None:
            if bool(changes["is_active"]) != expected_active:
                raise AppException(
                    code="product_status_mismatch",
                    message="status and is_active are inconsistent",
                    http_status=422,
                )
        changes["is_active"] = expected_active

    if "is_active" in changes and changes["is_active"] is not None:
        changes["is_active"] = bool(changes["is_active"])
        if "status" not in changes:
            changes["status"] = ProductStatus.ACTIVE if changes["is_active"] else ProductStatus.INACTIVE

    if "base_unit_id" in changes and changes["base_unit_id"] is not None:
        await _get_unit(session, tenant_id, changes["base_unit_id"])

    for field, value in changes.items():
        setattr(product, field, value)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_products_tenant_code" in message:
            raise AppException(
                code="product_code_exists",
                message="Product code already exists",
                http_status=409,
            ) from exc
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
