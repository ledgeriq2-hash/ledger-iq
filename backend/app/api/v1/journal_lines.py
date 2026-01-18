from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import require_perm
from app.schemas.dimensions import JournalLineDimensionsResponse, JournalLineDimensionsUpdate
from app.services.journal_line_dimension_service import JournalLineDimensionService

router = APIRouter(prefix="/journal-lines")


def _actor_context(request: Request, current_user: object) -> tuple[UUID | None, bool]:
    actor_id = getattr(request.state, "user_id", None)
    is_superuser = bool(getattr(current_user, "is_superuser", False))
    return actor_id, is_superuser


@router.get("/{line_id}/dimensions", response_model=JournalLineDimensionsResponse)
async def get_line_dimensions(
    line_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("dimension.view")),
):
    actor_id, is_superuser = _actor_context(request, current_user)
    service = JournalLineDimensionService(
        session=session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        is_superuser=is_superuser,
    )
    items = await service.get_line_dimensions(line_id)
    return JournalLineDimensionsResponse(journal_line_id=line_id, items=items)


@router.put("/{line_id}/dimensions", response_model=JournalLineDimensionsResponse)
async def set_line_dimensions(
    line_id: UUID,
    payload: JournalLineDimensionsUpdate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("journal.dimension.assign")),
):
    actor_id, is_superuser = _actor_context(request, current_user)
    service = JournalLineDimensionService(
        session=session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        is_superuser=is_superuser,
    )
    items = await service.set_line_dimensions(line_id, payload.dimensions)
    return JournalLineDimensionsResponse(journal_line_id=line_id, items=items)


__all__ = ["router"]
