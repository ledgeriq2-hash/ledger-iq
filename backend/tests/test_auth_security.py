from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_refresh_token_rotation_rejects_reuse(client: AsyncClient, register_owner):
    slug = f"rot-{uuid.uuid4().hex[:6]}"
    registration = await register_owner(slug=slug, email=f"{slug}@example.com")
    refresh_token = registration["tokens"]["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first.status_code == 200, first.text
    token2 = first.json()["refresh_token"]

    # Reusing the original token must fail
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert second.status_code in (401, 403)

    # New token should work
    third = await client.post("/api/v1/auth/refresh", json={"refresh_token": token2})
    assert third.status_code == 200, third.text


@pytest.mark.anyio
async def test_logout_revokes_refresh_token(client: AsyncClient, register_owner):
    slug = f"logout-{uuid.uuid4().hex[:6]}"
    registration = await register_owner(slug=slug, email=f"{slug}@example.com")
    refresh_token = registration["tokens"]["refresh_token"]

    logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 200, logout.text

    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse.status_code == 401


@pytest.mark.anyio
async def test_revoked_token_cannot_be_reused(client: AsyncClient, register_owner):
    slug = f"rev-{uuid.uuid4().hex[:6]}"
    registration = await register_owner(slug=slug, email=f"{slug}@example.com")
    refresh_token = registration["tokens"]["refresh_token"]

    # First refresh rotates and revokes the original
    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first.status_code == 200, first.text

    # Original token reuse must fail
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert second.status_code in (401, 403)
