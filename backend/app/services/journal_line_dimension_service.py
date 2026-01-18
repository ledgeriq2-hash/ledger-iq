from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.permissions import PermissionCode
from app.models.dimension import Dimension
from app.models.dimension_value import DimensionValue
from app.models.journal_entry import JournalEntry
from app.models.journal_line import JournalLine
from app.models.journal_line_dimension import JournalLineDimension
from app.schemas.dimensions import JournalLineDimensionItem
from app.services.audit_service import AuditService
from app.services.permission_service import require_permission


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _entry_is_posted(entry: JournalEntry) -> bool:
    return bool(entry.is_posted) or str(entry.status or "").lower() == "posted"


@dataclass(slots=True)
class JournalLineDimensionService:
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

    async def _load_line(self, line_id: UUID) -> JournalLine:
        line = await self.session.get(JournalLine, line_id)
        if not line or line.tenant_id != self.tenant_id:
            raise AppException(
                code="journal_line_not_found",
                message="Journal line not found",
                http_status=404,
            )
        return line

    async def _fetch_line_dimensions(self, line_id: UUID) -> list[JournalLineDimensionItem]:
        stmt = (
            select(Dimension, DimensionValue, JournalLineDimension)
            .join(DimensionValue, DimensionValue.id == JournalLineDimension.dimension_value_id)
            .join(Dimension, Dimension.id == DimensionValue.dimension_id)
            .where(
                JournalLineDimension.tenant_id == self.tenant_id,
                JournalLineDimension.journal_line_id == line_id,
                DimensionValue.tenant_id == self.tenant_id,
                Dimension.tenant_id == self.tenant_id,
            )
            .order_by(Dimension.key)
        )
        result = await self.session.execute(stmt)
        items: list[JournalLineDimensionItem] = []
        for dimension, value, _ in result.fetchall():
            items.append(
                JournalLineDimensionItem(
                    dimension_id=dimension.id,
                    dimension_key=dimension.key,
                    dimension_name=dimension.name,
                    value_id=value.id,
                    value_code=value.code,
                    value_name=value.name,
                )
            )
        return items

    async def get_line_dimensions(self, line_id: UUID) -> list[JournalLineDimensionItem]:
        await self._require_permission(PermissionCode.DIMENSION_VIEW.value)
        await self._load_line(line_id)
        return await self._fetch_line_dimensions(line_id)

    async def set_line_dimensions(
        self,
        line_id: UUID,
        dimensions: dict[str, UUID],
    ) -> list[JournalLineDimensionItem]:
        await self._require_permission(PermissionCode.JOURNAL_DIMENSION_ASSIGN.value)
        line = await self._load_line(line_id)
        if _entry_is_posted(line.entry):
            raise AppException(
                code="journal_line_posted_immutable",
                message="Posted journal line dimensions are immutable",
                http_status=409,
            )

        before_items = await self._fetch_line_dimensions(line_id)

        assignments: list[tuple[Dimension, DimensionValue]] = []
        for dimension_key, value_id in (dimensions or {}).items():
            key = _normalize_text(dimension_key)
            if not key:
                raise AppException(
                    code="dimension_key_required",
                    message="Dimension key is required",
                    http_status=422,
                )

            dimension_result = await self.session.execute(
                select(Dimension).where(
                    Dimension.tenant_id == self.tenant_id,
                    Dimension.key == key,
                )
            )
            dimension = dimension_result.scalar_one_or_none()
            if not dimension:
                raise AppException(
                    code="dimension_not_found",
                    message="Dimension not found",
                    http_status=404,
                )
            if not dimension.is_active:
                raise AppException(
                    code="dimension_inactive",
                    message="Dimension is inactive",
                    http_status=409,
                )

            value = await self.session.get(DimensionValue, value_id)
            if not value or value.tenant_id != self.tenant_id:
                raise AppException(
                    code="dimension_value_not_found",
                    message="Dimension value not found",
                    http_status=404,
                )
            if value.dimension_id != dimension.id:
                raise AppException(
                    code="dimension_value_mismatch",
                    message="Dimension value does not belong to the specified dimension",
                    http_status=409,
                )
            if not value.is_active:
                raise AppException(
                    code="dimension_value_inactive",
                    message="Dimension value is inactive",
                    http_status=409,
                )

            assignments.append((dimension, value))

        await self.session.execute(
            delete(JournalLineDimension).where(
                JournalLineDimension.tenant_id == self.tenant_id,
                JournalLineDimension.journal_line_id == line_id,
            )
        )

        for _, value in assignments:
            self.session.add(
                JournalLineDimension(
                    tenant_id=self.tenant_id,
                    journal_line_id=line_id,
                    dimension_value_id=value.id,
                )
            )

        await self.session.flush()
        after_items = await self._fetch_line_dimensions(line_id)

        audit = AuditService(self.session, self.tenant_id, self.actor_id)
        await audit.log(
            action="journal_line.dimensions.set",
            entity_type="journal_lines",
            entity_id=str(line.id),
            before={"dimensions": [item.model_dump(mode="json") for item in before_items]},
            after={"dimensions": [item.model_dump(mode="json") for item in after_items]},
            commit=False,
        )
        await self.session.commit()
        return after_items


__all__ = ["JournalLineDimensionService"]
