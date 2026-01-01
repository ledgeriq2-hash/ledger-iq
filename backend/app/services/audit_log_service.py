from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def record_audit_log(
    session: AsyncSession,
    tenant_id: UUID | None,
    table_name: str,
    record_id: str,
    action: str,
    *,
    user_id: UUID | None = None,
    old_data: dict | None = None,
    new_data: dict | None = None,
    commit: bool = True,
) -> AuditLog:
    log = AuditLog(
        tenant_id=tenant_id,
        table_name=table_name,
        record_id=str(record_id),
        action=action,
        user_id=user_id,
        old_data=old_data,
        new_data=new_data,
    )
    session.add(log)
    await session.flush()
    if commit:
        await session.commit()
    await session.refresh(log)
    return log


__all__ = ["record_audit_log"]
