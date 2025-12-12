import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_registration_creates_tenant_and_owner(client: AsyncClient, register_owner):
    slug = f"tenant-{uuid.uuid4().hex[:6]}"
    result = await register_owner(slug=slug, email=f"{slug}@example.com")
    assert "tenant" in result and "user" in result
    assert result["tenant"]["slug"] == slug
    assert result["user"]["email"] == f"{slug}@example.com"
    assert result["tokens"]["access_token"]


@pytest.mark.anyio
async def test_login_returns_tokens(client: AsyncClient, register_owner):
    slug = f"tenant-{uuid.uuid4().hex[:6]}"
    email = f"{slug}@example.com"
    password = "Secret123!"
    await register_owner(slug=slug, email=email, password=password)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "tenant": slug},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["tokens"]["access_token"]
    assert data["tokens"]["refresh_token"]


@pytest.mark.anyio
async def test_me_returns_current_user(client: AsyncClient, register_owner):
    slug = f"tenant-{uuid.uuid4().hex[:6]}"
    email = f"{slug}@example.com"
    register_data = await register_owner(slug=slug, email=email, password="Secret123!")
    access_token = register_data["tokens"]["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["email"] == email
    assert data["tenant"]["slug"] == slug


@pytest.mark.anyio
async def test_invalid_login_returns_401(client: AsyncClient, register_owner):
    slug = f"tenant-{uuid.uuid4().hex[:6]}"
    email = f"{slug}@example.com"
    password = "Secret123!"
    await register_owner(slug=slug, email=email, password=password)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong-password", "tenant": slug},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_refresh_with_cookie_returns_tokens(client: AsyncClient, register_owner):
    # Ensure refresh works when the token is provided via cookie.
    slug = f"tenant-{uuid.uuid4().hex[:6]}"
    register_data = await register_owner(slug=slug, email=f"{slug}@example.com", password="Secret123!")
    refresh_token = register_data["tokens"]["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": refresh_token},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]


@pytest.mark.anyio
async def test_refresh_with_body_returns_tokens(client: AsyncClient, register_owner):
    # Ensure refresh works when the token is provided in the request body.
    slug = f"tenant-{uuid.uuid4().hex[:6]}"
    register_data = await register_owner(slug=slug, email=f"{slug}@example.com", password="Secret123!")
    refresh_token = register_data["tokens"]["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
