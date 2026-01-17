from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import audit_log_service


@dataclass(slots=True)
class AuditService:
    session: AsyncSession
    tenant_id: UUID | None
    actor_id: UUID | None = None

    async def log(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        reason: str | None = None,
        before: dict | None = None,
        after: dict | None = None,
        period_year: int | None = None,
        period_month: int | None = None,
        commit: bool = False,
    ) -> None:
        payload = dict(after or {})
        if reason:
            payload["reason"] = reason
        if period_year is not None:
            payload["period_year"] = period_year
        if period_month is not None:
            payload["period_month"] = period_month

        await audit_log_service.record_audit_log(
            self.session,
            self.tenant_id,
            entity_type,
            entity_id,
            action,
            user_id=self.actor_id,
            old_data=before,
            new_data=payload or None,
            commit=commit,
        )


__all__ = ["AuditService"]
