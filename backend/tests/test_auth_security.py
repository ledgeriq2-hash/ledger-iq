from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_refresh_token_rotation_rejects_reuse(client: AsyncClient, register_owner):
    slug = f"rot-{uuid.uuid4().hex[:6]}"
    registration = await register_owner(slug=slug, email=f"{slug}@example.com")
    original_cookie = client.cookies.get("refresh_token")
    assert original_cookie

    first = await client.post("/api/v1/auth/refresh")
    assert first.status_code == 200, first.text
    rotated_cookie = first.cookies.get("refresh_token")
    assert rotated_cookie and rotated_cookie != original_cookie

    # Reusing the original token must fail
    client.cookies.clear()
    client.cookies.set("refresh_token", original_cookie, path="/")
    second = await client.post("/api/v1/auth/refresh")
    assert second.status_code in (401, 403), second.text

    # New token should work
    client.cookies.clear()
    client.cookies.set("refresh_token", rotated_cookie, path="/")
    third = await client.post("/api/v1/auth/refresh")
    assert third.status_code == 200, third.text


@pytest.mark.anyio
async def test_logout_revokes_refresh_token(client: AsyncClient, register_owner):
    slug = f"logout-{uuid.uuid4().hex[:6]}"
    registration = await register_owner(slug=slug, email=f"{slug}@example.com")
    assert client.cookies.get("refresh_token")

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 200, logout.text
    logout_set_cookie = logout.headers.get("set-cookie", "")
    assert "Max-Age=0" in logout_set_cookie or "expires=Thu" in logout_set_cookie

    reuse = await client.post("/api/v1/auth/refresh")
    assert reuse.status_code == 401, reuse.text


@pytest.mark.anyio
async def test_revoked_token_cannot_be_reused(client: AsyncClient, register_owner):
    slug = f"rev-{uuid.uuid4().hex[:6]}"
    registration = await register_owner(slug=slug, email=f"{slug}@example.com")
    original_cookie = client.cookies.get("refresh_token")
    assert original_cookie

    # First refresh rotates and revokes the original
    first = await client.post("/api/v1/auth/refresh")
    assert first.status_code == 200, first.text

    # Original token reuse must fail
    client.cookies.clear()
    client.cookies.set("refresh_token", original_cookie, path="/")
    second = await client.post("/api/v1/auth/refresh")
    assert second.status_code in (401, 403)


@pytest.mark.anyio
async def test_invalid_refresh_clears_cookie(client: AsyncClient):
    client.cookies.set("refresh_token", "invalid", path="/")

    response = await client.post("/api/v1/auth/refresh")

    assert response.status_code == 401, response.text
    set_cookie = response.headers.get("set-cookie", "")
    assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie


@pytest.mark.anyio
async def test_login_sets_refresh_cookie_and_refresh_rotates(client: AsyncClient, register_owner):
    slug = f"login-{uuid.uuid4().hex[:6]}"
    email = f"{slug}@example.com"
    password = "Secret123!"
    registration = await register_owner(slug=slug, email=email, password=password)

    # Fresh login request to ensure cookie is set by /login
    client.cookies.clear()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "tenant": slug},
        headers={"X-Tenant-Id": registration["tenant"]["id"]},
    )
    assert login.status_code == 200, login.text
    set_cookie_header = login.headers.get("set-cookie", "").lower()
    assert "refresh_token" in set_cookie_header
    assert "httponly" in set_cookie_header

    first_cookie = client.cookies.get("refresh_token")
    assert first_cookie

    refresh = await client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200, refresh.text
    rotated_cookie = client.cookies.get("refresh_token")
    assert rotated_cookie and rotated_cookie != first_cookie
