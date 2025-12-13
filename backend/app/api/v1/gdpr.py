from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import ADMIN, OWNER, require_roles
from app.models.gdpr_request import GdprRequest
from app.schemas.common import BaseSchema
from app.tasks import gdpr_tasks

router = APIRouter(prefix="/gdpr")


class ExportResponse(BaseSchema):
    tenant_id: UUID
    status: str
    request_id: UUID | None = None
    download_url: str | None = None


@router.post("/tenants/{tenant_id}/export", response_model=ExportResponse)
async def export_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    __ = Depends(require_roles([OWNER, ADMIN])),
):
    req = GdprRequest(tenant_id=tenant_id, action="export", status="pending", initiated_by=__ and getattr(__, "id", None))
    session.add(req)
    await session.commit()
    await session.refresh(req)
    gdpr_tasks.run_export.delay(str(req.id))
    return ExportResponse(tenant_id=tenant_id, status="scheduled", request_id=req.id)


@router.post("/tenants/{tenant_id}/delete", response_model=ExportResponse)
async def delete_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    __ = Depends(require_roles([OWNER, ADMIN])),
):
    req = GdprRequest(tenant_id=tenant_id, action="delete", status="pending", initiated_by=__ and getattr(__, "id", None))
    session.add(req)
    await session.commit()
    await session.refresh(req)
    gdpr_tasks.run_delete.delay(str(req.id))
    return ExportResponse(tenant_id=tenant_id, status="scheduled_delete", request_id=req.id)


@router.get("/requests/{request_id}", response_model=ExportResponse)
async def get_request_status(
    request_id: UUID,
    session: AsyncSession = Depends(deps.get_db),
    __ = Depends(require_roles([OWNER, ADMIN])),
):
    req = await session.get(GdprRequest, request_id)
    if not req:
        return ExportResponse(tenant_id=UUID(int=0), status="not_found")
    download_url = None
    if req.artifact_path:
        download_url = f"/downloads/{Path(req.artifact_path).name}"
    return ExportResponse(tenant_id=req.tenant_id, status=req.status, request_id=req.id, download_url=download_url)


__all__ = ["router"]
