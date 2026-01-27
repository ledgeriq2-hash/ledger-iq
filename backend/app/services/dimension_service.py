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


def _dimension_payload(dimension: Dimension) -> dict[str, Any]:
    return {
        "key": dimension.key,
        "name": dimension.name,
        "is_active": dimension.is_active,
    }


@dataclass(slots=True)
class DimensionService:
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

    async def list_dimensions(self) -> list[Dimension]:
        await self._require_permission(PermissionCode.DIMENSION_VIEW.value)
        result = await self.session.execute(
            select(Dimension).where(Dimension.tenant_id == self.tenant_id).order_by(Dimension.key)
        )
        return result.scalars().all()

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

    async def create_dimension(self, payload: Any) -> Dimension:
        await self._require_permission(PermissionCode.DIMENSION_MANAGE.value)
        data = _to_dict(payload)
        key = _normalize_text(data.get("key"))
        name = _normalize_text(data.get("name"))
        if not key:
            raise AppException(
                code="dimension_key_required",
                message="Dimension key is required",
                http_status=422,
            )
        if not name:
            raise AppException(
                code="dimension_name_required",
                message="Dimension name is required",
                http_status=422,
            )

        existing = await self.session.execute(
            select(Dimension.id).where(Dimension.tenant_id == self.tenant_id, Dimension.key == key)
        )
        if existing.scalar_one_or_none():
            raise AppException(
                code="dimension_key_exists",
                message="Dimension key already exists",
                http_status=409,
            )

        dimension = Dimension(
            tenant_id=self.tenant_id,
            key=key,
            name=name,
            is_active=True,
        )
        self.session.add(dimension)
        try:
            await self.session.flush()
            audit = AuditService(self.session, self.tenant_id, self.actor_id)
            await audit.log(
                action="dimension.create",
                entity_type="dimensions",
                entity_id=str(dimension.id),
                after=_dimension_payload(dimension),
                commit=False,
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            message = str(getattr(exc, "orig", exc))
            if "uq_dimensions_tenant_key" in message:
                raise AppException(
                    code="dimension_key_exists",
                    message="Dimension key already exists",
                    http_status=409,
                ) from exc
            raise
        await self.session.refresh(dimension)
        return dimension

    async def update_dimension(self, dimension_id: UUID, payload: Any) -> Dimension:
        await self._require_permission(PermissionCode.DIMENSION_MANAGE.value)
        dimension = await self._load_dimension(dimension_id)

        data = _to_dict(payload, exclude_unset=True)
        changes: dict[str, Any] = {}
        if "key" in data:
            key = _normalize_text(data.get("key"))
            if not key:
                raise AppException(
                    code="dimension_key_required",
                    message="Dimension key is required",
                    http_status=422,
                )
            if key != dimension.key:
                existing = await self.session.execute(
                    select(Dimension.id).where(
                        Dimension.tenant_id == self.tenant_id,
                        Dimension.key == key,
                        Dimension.id != dimension.id,
                    )
                )
                if existing.scalar_one_or_none():
                    raise AppException(
                        code="dimension_key_exists",
                        message="Dimension key already exists",
                        http_status=409,
                    )
                changes["key"] = key
        if "name" in data:
            name = _normalize_text(data.get("name"))
            if not name:
                raise AppException(
                    code="dimension_name_required",
                    message="Dimension name is required",
                    http_status=422,
                )
            if name != dimension.name:
                changes["name"] = name

        if not changes:
            return dimension

        before = {field: getattr(dimension, field) for field in changes}
        for field, value in changes.items():
            setattr(dimension, field, value)

        await self.session.flush()
        after = {field: getattr(dimension, field) for field in changes}
        audit = AuditService(self.session, self.tenant_id, self.actor_id)
        await audit.log(
            action="dimension.update",
            entity_type="dimensions",
            entity_id=str(dimension.id),
            before=before,
            after=after,
            commit=False,
        )
        await self.session.commit()
        await self.session.refresh(dimension)
        return dimension

    async def archive_dimension(self, dimension_id: UUID) -> Dimension:
        await self._require_permission(PermissionCode.DIMENSION_MANAGE.value)
        dimension = await self._load_dimension(dimension_id)
        if not dimension.is_active:
            return dimension

        before = {"is_active": dimension.is_active}
        dimension.is_active = False
        await self.session.flush()
        audit = AuditService(self.session, self.tenant_id, self.actor_id)
        await audit.log(
            action="dimension.archive",
            entity_type="dimensions",
            entity_id=str(dimension.id),
            before=before,
            after={"is_active": dimension.is_active},
            commit=False,
        )
        await self.session.commit()
        await self.session.refresh(dimension)
        return dimension


__all__ = ["DimensionService"]
