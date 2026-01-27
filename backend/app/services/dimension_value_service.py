from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.permissions import PermissionCode
from app.models.dimension import Dimension
from app.models.dimension_value import DimensionValue
from app.services.audit_service import AuditService
from app.services.permission_service import require_permission


def _to_dict(payload: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=exclude_unset)
    if isinstance(payload, dict):
        return payload
    raise TypeError("payload must be a mapping or pydantic model")


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _dimension_value_payload(value: DimensionValue) -> dict[str, Any]:
    return {
        "dimension_id": str(value.dimension_id),
        "code": value.code,
        "name": value.name,
        "is_active": value.is_active,
    }


@dataclass(slots=True)
class DimensionValueService:
    session: AsyncSession
    tenant_id: UUID
    actor_id: UUID | None = None
    is_superuser: bool = False

    async def _require_permission(self, permission_code: str) -> None:
        if self.is_superuser:
            return
        await require_permission(
            self.session,
            tenant_id=self.tenant_id,
            actor_id=self.actor_id,
            permission_code=permission_code,
        )

    async def _load_dimension(self, dimension_id: UUID) -> Dimension:
        result = await self.session.execute(
            select(Dimension).where(Dimension.id == dimension_id, Dimension.tenant_id == self.tenant_id)
        )
        dimension = result.scalar_one_or_none()
        if not dimension:
            raise AppException(
                code="dimension_not_found",
                message="Dimension not found",
                http_status=404,
            )
        return dimension

    async def _load_value(self, value_id: UUID) -> DimensionValue:
        result = await self.session.execute(
            select(DimensionValue).where(DimensionValue.id == value_id, DimensionValue.tenant_id == self.tenant_id)
        )
        value = result.scalar_one_or_none()
        if not value:
            raise AppException(
                code="dimension_value_not_found",
                message="Dimension value not found",
                http_status=404,
            )
        return value

    async def list_values(self, dimension_id: UUID) -> list[DimensionValue]:
        await self._require_permission(PermissionCode.DIMENSION_VALUE_VIEW.value)
        _ = await self._load_dimension(dimension_id)
        result = await self.session.execute(
            select(DimensionValue)
            .where(
                DimensionValue.tenant_id == self.tenant_id,
                DimensionValue.dimension_id == dimension_id,
            )
            .order_by(DimensionValue.code)
        )
        return result.scalars().all()

    async def create_value(self, dimension_id: UUID, payload: Any) -> DimensionValue:
        await self._require_permission(PermissionCode.DIMENSION_VALUE_MANAGE.value)
        dimension = await self._load_dimension(dimension_id)
        if not dimension.is_active:
            raise AppException(
                code="dimension_inactive",
                message="Dimension is inactive",
                http_status=409,
            )

        data = _to_dict(payload)
        code = _normalize_text(data.get("code"))
        name = _normalize_text(data.get("name"))
        if not code:
            raise AppException(
                code="dimension_value_code_required",
                message="Dimension value code is required",
                http_status=422,
            )
        if not name:
            raise AppException(
                code="dimension_value_name_required",
                message="Dimension value name is required",
                http_status=422,
            )

        existing = await self.session.execute(
            select(DimensionValue.id).where(
                DimensionValue.tenant_id == self.tenant_id,
                DimensionValue.dimension_id == dimension_id,
                DimensionValue.code == code,
            )
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="dimension_value_code_exists",
                message="Dimension value code already exists",
                http_status=409,
            )

        value = DimensionValue(
            tenant_id=self.tenant_id,
            dimension_id=dimension_id,
            code=code,
            name=name,
            is_active=True,
        )
        self.session.add(value)
        try:
            await self.session.flush()
            audit = AuditService(self.session, self.tenant_id, self.actor_id)
            await audit.log(
                action="dimension_value.create",
                entity_type="dimension_values",
                entity_id=str(value.id),
                after=_dimension_value_payload(value),
                commit=False,
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            message = str(getattr(exc, "orig", exc))
            if "uq_dimension_values_tenant_dimension_code" in message:
                raise AppException(
                    code="dimension_value_code_exists",
                    message="Dimension value code already exists",
                    http_status=409,
                ) from exc
            raise
        await self.session.refresh(value)
        return value

    async def update_value(self, value_id: UUID, payload: Any) -> DimensionValue:
        await self._require_permission(PermissionCode.DIMENSION_VALUE_MANAGE.value)
        value = await self._load_value(value_id)

        data = _to_dict(payload, exclude_unset=True)
        changes: dict[str, Any] = {}
        if "code" in data:
            code = _normalize_text(data.get("code"))
            if not code:
                raise AppException(
                    code="dimension_value_code_required",
                    message="Dimension value code is required",
                    http_status=422,
                )
            if code != value.code:
                existing = await self.session.execute(
                    select(DimensionValue.id).where(
                        DimensionValue.tenant_id == self.tenant_id,
                        DimensionValue.dimension_id == value.dimension_id,
                        DimensionValue.code == code,
                        DimensionValue.id != value.id,
                    )
                )
                if existing.scalar_one_or_none():
                    raise AppException(
                        code="dimension_value_code_exists",
                        message="Dimension value code already exists",
                        http_status=409,
                    )
                changes["code"] = code
        if "name" in data:
            name = _normalize_text(data.get("name"))
            if not name:
                raise AppException(
                    code="dimension_value_name_required",
                    message="Dimension value name is required",
                    http_status=422,
                )
            if name != value.name:
                changes["name"] = name

        if not changes:
            return value

        before = {field: getattr(value, field) for field in changes}
        for field, new_value in changes.items():
            setattr(value, field, new_value)
        await self.session.flush()
        after = {field: getattr(value, field) for field in changes}
        audit = AuditService(self.session, self.tenant_id, self.actor_id)
        await audit.log(
            action="dimension_value.update",
            entity_type="dimension_values",
            entity_id=str(value.id),
            before=before,
            after=after,
            commit=False,
        )
        await self.session.commit()
        await self.session.refresh(value)
        return value

    async def archive_value(self, value_id: UUID) -> DimensionValue:
        await self._require_permission(PermissionCode.DIMENSION_VALUE_MANAGE.value)
        value = await self._load_value(value_id)
        if not value.is_active:
            return value

        before = {"is_active": value.is_active}
        value.is_active = False
        await self.session.flush()
        audit = AuditService(self.session, self.tenant_id, self.actor_id)
        await audit.log(
            action="dimension_value.archive",
            entity_type="dimension_values",
            entity_id=str(value.id),
            before=before,
            after={"is_active": value.is_active},
            commit=False,
        )
        await self.session.commit()
        await self.session.refresh(value)
        return value


__all__ = ["DimensionValueService"]
