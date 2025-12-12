from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ADMIN, OWNER, require_roles
from app.schemas.common import BaseSchema

router = APIRouter(prefix="/gdpr")


class ExportResponse(BaseSchema):
    tenant_id: UUID
    status: str


@router.post("/tenants/{tenant_id}/export", response_model=ExportResponse)
async def export_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    __ = Depends(require_roles([OWNER, ADMIN])),
):
    # Stub: actual export should stream files; we only acknowledge request to keep backward compatibility.
    return ExportResponse(tenant_id=tenant_id, status="scheduled")


@router.post("/tenants/{tenant_id}/delete", response_model=ExportResponse)
async def delete_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    __ = Depends(require_roles([OWNER, ADMIN])),
):
    # Stub for GDPR delete; should be asynchronous in production.
    return ExportResponse(tenant_id=tenant_id, status="scheduled_delete")


__all__ = ["router"]
