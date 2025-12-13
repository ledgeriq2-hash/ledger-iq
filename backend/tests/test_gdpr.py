from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from app.config import get_settings
from app.database import async_session_maker
from app.models.feedback import Feedback
from app.models.gdpr_request import GdprRequest
from app.models.tenant import Tenant
from app.tasks import gdpr_tasks


@pytest.mark.anyio
async def test_gdpr_export_creates_artifact(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(tmp_path))
    async with async_session_maker() as session:
        tenant = Tenant(name="ExportCo", slug=f"exp-{uuid4().hex[:6]}")
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        req = GdprRequest(tenant_id=tenant.id, action="export", status="pending")
        session.add(req)
        await session.commit()
        await session.refresh(req)

        gdpr_tasks.run_export(str(req.id))
        await session.refresh(req)
        assert req.status == "ready"
        assert req.artifact_path is not None
        assert Path(req.artifact_path).exists()


@pytest.mark.anyio
async def test_gdpr_delete_removes_tenant_data(tmp_path, monkeypatch):
    monkeypatch.chdir(Path(tmp_path))
    settings = get_settings()
    settings.gdpr_financial_retention_days = 0
    async with async_session_maker() as session:
        tenant = Tenant(name="DeleteCo", slug=f"del-{uuid4().hex[:6]}")
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)

        feedback = Feedback(tenant_id=tenant.id, category="bug", message="remove me")
        session.add(feedback)
        req = GdprRequest(tenant_id=tenant.id, action="delete", status="pending")
        session.add(req)
        await session.commit()
        await session.refresh(req)

        gdpr_tasks.run_delete(str(req.id))
        await session.refresh(req)
        assert req.status == "deleted"
        remaining = await session.execute(
            Feedback.__table__.select().where(Feedback.tenant_id == tenant.id)
        )
        assert remaining.fetchall() == []
