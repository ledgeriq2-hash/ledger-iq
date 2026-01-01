from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.audit_log import AuditLog


def build_audit_log(
    *,
    tenant_id: UUID,
    actor_id: UUID | None,
    action: str,
    reference_type: str,
    reference_id: UUID,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    return AuditLog(
        tenant_id=tenant_id,
        user_id=actor_id,
        action=action,
        table_name=reference_type,
        record_id=str(reference_id),
        old_data=None,
        new_data={
            "reference_type": reference_type,
            "reference_id": str(reference_id),
            "details": details or {},
        },
    )


__all__ = ["build_audit_log"]

