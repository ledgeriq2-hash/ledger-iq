from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback


async def create_feedback(session: AsyncSession, tenant_id: UUID, user_id: UUID | None, category: str, message: str) -> Feedback:
    feedback = Feedback(tenant_id=tenant_id, user_id=user_id, category=category, message=message)
    session.add(feedback)
    await session.commit()
    await session.refresh(feedback)
    return feedback


async def list_feedback(
    session: AsyncSession,
    *,
    tenant_id: UUID | None = None,
    category: str | None = None,
    limit: int = 100,
) -> Sequence[Feedback]:
    query = select(Feedback).order_by(Feedback.created_at.desc()).limit(limit)
    conditions = []
    if tenant_id:
        conditions.append(Feedback.tenant_id == tenant_id)
    if category:
        conditions.append(Feedback.category == category)
    if conditions:
        query = query.where(*conditions)
    result = await session.execute(query)
    return result.scalars().all()


__all__ = ["create_feedback", "list_feedback"]
