from __future__ import annotations

from datetime import datetime, UTC
from decimal import Decimal
import uuid

import pytest
from httpx import AsyncClient

from app.database import async_session_maker
from app.models.ai_log import AiLog


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_ai_overview_is_tenant_isolated(client: AsyncClient, register_owner):
    owner_one = await register_owner()
    token_one = owner_one["tokens"]["access_token"]
    tenant_one = uuid.UUID(owner_one["tenant"]["id"])

    owner_two = await register_owner()
    tenant_two = uuid.UUID(owner_two["tenant"]["id"])

    async with async_session_maker() as session:
        now = datetime.now(UTC)
        session.add_all(
            [
                AiLog(
                    tenant_id=tenant_one,
                    model_type="anomaly",
                    input_data="{}",
                    output_data='{"anomalies": [{"value": 1}]}',
                    score=Decimal("0.9"),
                    created_at=now,
                ),
                AiLog(
                    tenant_id=tenant_one,
                    model_type="forecast",
                    input_data="{}",
                    output_data='{"summary": "Growth expected", "forecast": [1, 2, 3]}',
                    created_at=now,
                ),
                AiLog(
                    tenant_id=tenant_two,
                    model_type="anomaly",
                    input_data="{}",
                    output_data='{"anomalies": []}',
                    created_at=now,
                ),
            ]
        )
        await session.commit()

    res = await client.get("/api/v1/ai/overview", headers=auth_headers(token_one))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["anomalies_count"] == 1
    assert "Growth expected" in data["forecast_summary"]["text"]
    assert len(data["alerts"]) == 2

    res_other = await client.get("/api/v1/ai/overview", headers=auth_headers(owner_two["tokens"]["access_token"]))
    assert res_other.status_code == 200
    data_other = res_other.json()
    assert data_other["anomalies_count"] == 1
    assert len(data_other["alerts"]) == 1
