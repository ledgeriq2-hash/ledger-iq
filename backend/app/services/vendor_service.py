from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.pagination import PaginationParams, paginate_query
from app.models.vendor import Vendor, VendorStatus


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


async def list_vendors(
    session: AsyncSession,
    tenant_id: UUID,
    params: PaginationParams,
    *,
    search: str | None = None,
    status: VendorStatus | str | None = None,
) -> tuple[list[Vendor], int]:
    statement = select(Vendor).where(Vendor.tenant_id == tenant_id)
    if search:
        term = search.strip()
        if term:
            pattern = f"%{term}%"
            statement = statement.where(or_(Vendor.code.ilike(pattern), Vendor.name.ilike(pattern)))
    if status:
        try:
            normalized = status if isinstance(status, VendorStatus) else VendorStatus(str(status))
        except Exception as exc:
            raise AppException(
                code="vendor_status_invalid",
                message="Vendor status is invalid",
                http_status=422,
            ) from exc
        statement = statement.where(Vendor.status == normalized)
    statement = statement.order_by(Vendor.created_at.desc())
    return await paginate_query(session, statement, params)


async def get_vendor(session: AsyncSession, tenant_id: UUID, vendor_id: UUID) -> Vendor | None:
    result = await session.execute(
        select(Vendor).where(Vendor.id == vendor_id, Vendor.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_vendor(
    session: AsyncSession,
    tenant_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> Vendor:
    _ = actor_id
    data = _to_dict(payload)
    if "metadata" in data and "metadata_json" not in data:
        data["metadata_json"] = data.pop("metadata")
    status = data.get("status")
    if status is not None:
        try:
            status = VendorStatus(status)
        except Exception as exc:
            raise AppException(
                code="vendor_status_invalid",
                message="Vendor status is invalid",
                http_status=422,
            ) from exc
        data["status"] = status
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    if not code:
        raise AppException(code="vendor_code_required", message="Vendor code is required", http_status=422)
    if not name:
        raise AppException(code="vendor_name_required", message="Vendor name is required", http_status=422)
    data["code"] = code
    data["name"] = name

    existing = await session.execute(
        select(Vendor.id).where(Vendor.tenant_id == tenant_id, Vendor.code == data.get("code"))
    )
    if existing.scalar_one_or_none():
        raise AppException(code="vendor_code_exists", message="Vendor code already exists", http_status=409)

    vendor = Vendor(**data, tenant_id=tenant_id)
    session.add(vendor)
    try:
        await session.flush()
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_vendors_tenant_code" in message or "vendors_tenant_id_code" in message:
            raise AppException(
                code="vendor_code_exists",
                message="Vendor code already exists",
                http_status=409,
            ) from exc
        raise
    await session.refresh(vendor)
    return vendor


async def update_vendor(
    session: AsyncSession,
    tenant_id: UUID,
    vendor_id: UUID,
    payload: Any,
    *,
    actor_id: UUID | None = None,
) -> Vendor | None:
    _ = actor_id
    vendor = await get_vendor(session, tenant_id, vendor_id)
    if not vendor:
        return None
    data = _to_dict(payload, exclude_unset=True)
    if "metadata" in data and "metadata_json" not in data:
        data["metadata_json"] = data.pop("metadata")

    allowed_fields = {
        "code",
        "name",
        "status",
        "currency_code",
        "payment_terms_days",
        "notes",
        "metadata_json",
    }
    changes = {field: value for field, value in data.items() if field in allowed_fields}
    if not changes:
        return vendor
    if "code" in changes:
        code = (changes.get("code") or "").strip()
        if not code:
            raise AppException(code="vendor_code_required", message="Vendor code is required", http_status=422)
        existing = await session.execute(
            select(Vendor.id).where(
                Vendor.tenant_id == tenant_id,
                Vendor.code == code,
                Vendor.id != vendor_id,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(code="vendor_code_exists", message="Vendor code already exists", http_status=409)
        changes["code"] = code
    if "name" in changes:
        name = (changes.get("name") or "").strip()
        if not name:
            raise AppException(code="vendor_name_required", message="Vendor name is required", http_status=422)
        changes["name"] = name
    if "status" in changes and changes["status"] is not None:
        try:
            changes["status"] = VendorStatus(changes["status"])
        except Exception as exc:
            raise AppException(
                code="vendor_status_invalid",
                message="Vendor status is invalid",
                http_status=422,
            ) from exc

    for field, value in changes.items():
        setattr(vendor, field, value)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        message = str(getattr(exc, "orig", exc))
        if "uq_vendors_tenant_code" in message or "vendors_tenant_id_code" in message:
            raise AppException(
                code="vendor_code_exists",
                message="Vendor code already exists",
                http_status=409,
            ) from exc
        raise
    await session.refresh(vendor)
    return vendor


__all__ = [
    "list_vendors",
    "get_vendor",
    "create_vendor",
    "update_vendor",
]
