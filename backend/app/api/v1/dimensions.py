from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.permissions import require_perm
from app.schemas.dimensions import (
    DimensionCreate,
    DimensionList,
    DimensionPublic,
    DimensionUpdate,
    DimensionValueCreate,
    DimensionValueList,
    DimensionValuePublic,
    DimensionValueUpdate,
)
from app.services.dimension_service import DimensionService
from app.services.dimension_value_service import DimensionValueService

router = APIRouter(prefix="/dimensions")


def _actor_context(request: Request, current_user: object) -> tuple[UUID | None, bool]:
    actor_id = getattr(request.state, "user_id", None)
    is_superuser = bool(getattr(current_user, "is_superuser", False))
    return actor_id, is_superuser


@router.get("/", response_model=DimensionList)
async def list_dimensions(
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("dimension.view")),
):
    actor_id, is_superuser = _actor_context(request, current_user)
    service = DimensionService(session=session, tenant_id=tenant_id, actor_id=actor_id, is_superuser=is_superuser)
    return DimensionList(items=await service.list_dimensions())


@router.post("/", response_model=DimensionPublic, status_code=status.HTTP_201_CREATED)
async def create_dimension(
    payload: DimensionCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("dimension.manage")),
):
    actor_id, is_superuser = _actor_context(request, current_user)
    service = DimensionService(session=session, tenant_id=tenant_id, actor_id=actor_id, is_superuser=is_superuser)
    return await service.create_dimension(payload)


@router.patch("/{dimension_id}", response_model=DimensionPublic)
async def update_dimension(
    dimension_id: UUID,
    payload: DimensionUpdate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("dimension.manage")),
):
    actor_id, is_superuser = _actor_context(request, current_user)
    service = DimensionService(session=session, tenant_id=tenant_id, actor_id=actor_id, is_superuser=is_superuser)
    return await service.update_dimension(dimension_id, payload)


@router.post("/{dimension_id}/archive", response_model=DimensionPublic)
async def archive_dimension(
    dimension_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("dimension.manage")),
):
    actor_id, is_superuser = _actor_context(request, current_user)
    service = DimensionService(session=session, tenant_id=tenant_id, actor_id=actor_id, is_superuser=is_superuser)
    return await service.archive_dimension(dimension_id)


@router.get("/{dimension_id}/values", response_model=DimensionValueList)
async def list_dimension_values(
    dimension_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("dimension_value.view")),
):
    actor_id, is_superuser = _actor_context(request, current_user)
    service = DimensionValueService(
        session=session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        is_superuser=is_superuser,
    )
    values = await service.list_values(dimension_id)
    return DimensionValueList(items=values)


@router.post("/{dimension_id}/values", response_model=DimensionValuePublic, status_code=status.HTTP_201_CREATED)
async def create_dimension_value(
    dimension_id: UUID,
    payload: DimensionValueCreate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("dimension_value.manage")),
):
    actor_id, is_superuser = _actor_context(request, current_user)
    service = DimensionValueService(
        session=session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        is_superuser=is_superuser,
    )
    return await service.create_value(dimension_id, payload)


@router.patch("/values/{value_id}", response_model=DimensionValuePublic)
async def update_dimension_value(
    value_id: UUID,
    payload: DimensionValueUpdate,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("dimension_value.manage")),
):
    actor_id, is_superuser = _actor_context(request, current_user)
    service = DimensionValueService(
        session=session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        is_superuser=is_superuser,
    )
    return await service.update_value(value_id, payload)


@router.post("/values/{value_id}/archive", response_model=DimensionValuePublic)
async def archive_dimension_value(
    value_id: UUID,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    tenant_id: UUID = Depends(deps.get_current_tenant),
    current_user: object = Depends(deps.get_current_active_user),
    __: object = Depends(require_perm("dimension_value.manage")),
):
    actor_id, is_superuser = _actor_context(request, current_user)
    service = DimensionValueService(
        session=session,
        tenant_id=tenant_id,
        actor_id=actor_id,
        is_superuser=is_superuser,
    )
    return await service.archive_value(value_id)


__all__ = ["router"]
