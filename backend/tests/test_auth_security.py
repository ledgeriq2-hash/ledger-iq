from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.anyio
async def test_refresh_token_rotation_rejects_reuse(client: AsyncClient, register_owner):
    slug = f"rot-{uuid.uuid4().hex[:6]}"
    registration = await register_owner(slug=slug, email=f"{slug}@example.com")
    refresh_token = registration["tokens"]["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first.status_code == 200, first.text
    # Reusing the same refresh token should be revoked
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert second.status_code == 401


@pytest.mark.anyio
async def test_logout_revokes_refresh_token(client: AsyncClient, register_owner):
    slug = f"logout-{uuid.uuid4().hex[:6]}"
    registration = await register_owner(slug=slug, email=f"{slug}@example.com")
    refresh_token = registration["tokens"]["refresh_token"]

    logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 200, logout.text

    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse.status_code == 401
