from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_optional_routes_auth_billing_ai(client: AsyncClient):
    tenant_slug = f"tenant-{uuid.uuid4().hex[:6]}"
    email = f"{tenant_slug}@example.com"
    password = "Secret123!"
    register_payload = {
        "tenant": {"name": f"Tenant {tenant_slug}", "slug": tenant_slug},
        "admin": {"email": email, "password": password, "full_name": "Owner"},
    }

    register_resp = await client.post("/api/v1/auth/register", json=register_payload)
    assert register_resp.status_code == 201, register_resp.text
    register_data = register_resp.json()
    access_token = register_data["tokens"]["access_token"]
    tenant_id = register_data["tenant"]["id"]
    refresh_token = register_resp.cookies.get("refresh_token")
    assert refresh_token, "refresh token cookie not set"

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "tenant": tenant_slug},
        headers={"X-Tenant-Id": tenant_id},
    )
    assert login_resp.status_code == 200, login_resp.text
    login_data = login_resp.json()
    login_token = login_data["tokens"]["access_token"]
    login_refresh = login_resp.cookies.get("refresh_token")
    assert login_refresh

    me_resp = await client.get("/api/v1/auth/me", headers=_auth_headers(login_token))
    assert me_resp.status_code == 200, me_resp.text

    refresh_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": login_refresh})
    assert refresh_resp.status_code == 200, refresh_resp.text

    logout_resp = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 200, logout_resp.text

    settings_resp = await client.get("/api/v1/settings/", headers=_auth_headers(access_token))
    assert settings_resp.status_code == 200, settings_resp.text

    update_resp = await client.put(
        "/api/v1/settings/",
        json={"theme": {"primary": "#4EB7B3"}},
        headers=_auth_headers(access_token),
    )
    assert update_resp.status_code == 200, update_resp.text

    dashboard_resp = await client.get("/api/v1/dashboard/summary", headers=_auth_headers(access_token))
    assert dashboard_resp.status_code == 200, dashboard_resp.text

    debts_resp = await client.get("/api/v1/debts/", headers=_auth_headers(access_token))
    assert debts_resp.status_code == 200, debts_resp.text
    assert debts_resp.json()["total"] == 0

    dev_resp = await client.get("/api/v1/dev/info", headers=_auth_headers(access_token))
    assert dev_resp.status_code == 200, dev_resp.text

    ml_status = await client.get("/api/v1/ml/status", headers=_auth_headers(access_token))
    assert ml_status.status_code == 200, ml_status.text

    ml_ingest = await client.post("/api/v1/ml/predictions/ingest", headers=_auth_headers(access_token))
    assert ml_ingest.status_code == 501, ml_ingest.text
    assert ml_ingest.json()["code"] == "ml_not_available"

    plans_resp = await client.get("/api/v1/billing/plans", headers=_auth_headers(access_token))
    assert plans_resp.status_code == 200, plans_resp.text

    overview_resp = await client.get("/api/v1/billing/overview", headers=_auth_headers(access_token))
    assert overview_resp.status_code == 200, overview_resp.text

    ai_summary = await client.post(
        "/api/v1/ai/summary",
        json={"balance_sheet": {"cash": 1000}, "income_statement": {"revenue": 2000, "net_income": 250}},
        headers=_auth_headers(access_token),
    )
    assert ai_summary.status_code == 200, ai_summary.text

    ai_overview = await client.get("/api/v1/ai/overview", headers=_auth_headers(access_token))
    assert ai_overview.status_code == 200, ai_overview.text

    ai_run = await client.post("/api/v1/ai/run", headers=_auth_headers(access_token))
    assert ai_run.status_code == 200, ai_run.text

    logout_all_resp = await client.post("/api/v1/auth/logout-all", headers=_auth_headers(access_token))
    assert logout_all_resp.status_code == 200, logout_all_resp.text
