from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.models.ai_run import AiRun
from app.schemas.ai_runs_v1 import AiRunCreateRequest
from app.utils.ai_hashing import canonical_sha256


def _normalize_limit_offset(limit: int, offset: int) -> tuple[int, int]:
    normalized_limit = limit if limit > 0 else DEFAULT_PAGE_SIZE
    normalized_limit = min(normalized_limit, MAX_PAGE_SIZE)
    normalized_offset = max(0, offset)
    return normalized_limit, normalized_offset


def _normalize_status(status: str | None) -> str | None:
    if status is None:
        return None
    value = status.strip().lower()
    if not value:
        return None
    if value not in {"approved", "revoked"}:
        raise AppException(code="ai_run_status_invalid", message="AI run status is invalid", http_status=422)
    return value


async def create_run(
    *,
    db: AsyncSession,
    client_id: UUID,
    req: AiRunCreateRequest,
) -> AiRun:
    payload_hash = canonical_sha256(req.payload)
    run = AiRun(
        client_id=client_id,
        schema_version=req.schema_version,
        model_name=req.run_meta.model_name,
        model_version=req.run_meta.model_version,
        dataset_fingerprint=req.run_meta.dataset_fingerprint,
        date_from=req.run_meta.date_from,
        date_to=req.run_meta.date_to,
        scenario=req.run_meta.scenario,
        status="approved",
        payload_hash=payload_hash,
        payload_json=req.payload,
        signature=req.signature,
        created_by=req.run_meta.created_by,
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


async def list_runs(
    *,
    db: AsyncSession,
    client_id: UUID,
    status: str | None = None,
    scenario: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> list[AiRun]:
    normalized_limit, normalized_offset = _normalize_limit_offset(limit, offset)
    statement = select(AiRun).where(AiRun.client_id == client_id)
    normalized_status = _normalize_status(status)
    if normalized_status:
        statement = statement.where(AiRun.status == normalized_status)
    if scenario:
        scenario_value = scenario.strip()
        if scenario_value:
            statement = statement.where(AiRun.scenario == scenario_value)
    statement = statement.order_by(AiRun.created_at.desc()).limit(normalized_limit).offset(normalized_offset)
    result = await db.execute(statement)
    return list(result.scalars().all())


async def get_run(
    *,
    db: AsyncSession,
    client_id: UUID,
    run_id: UUID,
) -> AiRun:
    result = await db.execute(
        select(AiRun).where(AiRun.id == run_id, AiRun.client_id == client_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise AppException(code="ai_run_not_found", message="AI run not found", http_status=404)
    return run


async def revoke_run(
    *,
    db: AsyncSession,
    client_id: UUID,
    run_id: UUID,
    revoked_by: str | None = None,
    reason: str | None = None,
) -> AiRun:
    run = await get_run(db=db, client_id=client_id, run_id=run_id)
    if run.status == "revoked":
        raise AppException(code="ai_run_already_revoked", message="AI run already revoked", http_status=409)
    run.status = "revoked"
    run.revoked_at = datetime.now(UTC)
    run.revoked_by = revoked_by
    run.revoke_reason = reason
    await db.commit()
    await db.refresh(run)
    return run


__all__ = ["create_run", "list_runs", "get_run", "revoke_run"]
