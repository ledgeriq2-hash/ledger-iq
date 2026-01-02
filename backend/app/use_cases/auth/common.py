from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse

from app.core.exceptions import json_error_response
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.core.soft_launch import is_soft_launch_tenant
from app.schemas.auth import Token
from app.services import tenant_service
from app.services import user_service

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


@dataclass
class IssuedTokens:
    token: Token
    refresh_token: str
    refresh_expires_at: datetime


def exp_to_datetime(exp_value: int | datetime | None, fallback_seconds: int) -> datetime:
    if isinstance(exp_value, datetime):
        return exp_value if exp_value.tzinfo else exp_value.replace(tzinfo=UTC)
    try:
        exp_int = int(exp_value) if exp_value is not None else None
    except (TypeError, ValueError):
        exp_int = None
    if exp_int:
        return datetime.fromtimestamp(exp_int, tz=UTC)
    return datetime.now(UTC) + timedelta(seconds=fallback_seconds)


def build_claims(user, tenant_id: uuid.UUID, token_version: int) -> dict[str, object]:
    role_name = user.role.name if user.role else (str(user.role_id) if user.role_id else None)
    permissions = user.role.permissions_json if user.role else None
    return {
        "tenant_id": str(tenant_id),
        "role": role_name,
        "permissions": permissions or [],
        "token_version": token_version,
    }


async def issue_token_pair(session, settings, user, tenant_id: uuid.UUID, token_version: int, *, request=None) -> IssuedTokens:
    claims = build_claims(user, tenant_id, token_version)
    access_token = create_access_token(
        subject=str(user.id),
        claims=claims,
        expires_minutes=settings.access_token_expires_minutes,
    )
    refresh_token = create_refresh_token(
        subject=str(user.id),
        claims=claims,
        expires_days=settings.refresh_token_expires_days,
    )
    refresh_payload = decode_token(refresh_token, refresh=True)
    refresh_exp = exp_to_datetime(
        refresh_payload.get("exp"),
        fallback_seconds=settings.refresh_token_expires_days * 24 * 60 * 60,
    )
    user_agent = request.headers.get("User-Agent") if request else None
    ip_address = request.client.host if request and request.client else None
    await user_service.store_refresh_token(
        session, tenant_id, user.id, refresh_token, refresh_exp, user_agent=user_agent, ip_address=ip_address
    )
    token = Token(
        access_token=access_token,
        expires_in=settings.access_token_expires_minutes * 60 if settings.access_token_expires_minutes else None,
    )
    return IssuedTokens(token=token, refresh_token=refresh_token, refresh_expires_at=refresh_exp)


def ensure_refresh_token_type(decoded: dict[str, object]) -> None:
    token_type = decoded.get("type")
    if token_type not in (None, "refresh"):
        raise ValueError("Invalid refresh token type")


def cookie_params(settings):
    secure = bool(getattr(settings, "refresh_cookie_secure", False)) or str(
        getattr(settings, "environment", "production")
    ).lower() in {"production", "prod"}
    samesite = (getattr(settings, "refresh_cookie_samesite", "lax") or "lax").lower()
    if samesite not in {"lax", "strict", "none"}:
        samesite = "lax"
    path = getattr(settings, "refresh_cookie_path", "/") or "/"
    return {"secure": secure, "samesite": samesite, "path": path}


def set_refresh_cookie(response: JSONResponse, settings, token: str, expires_at: datetime) -> None:
    params = cookie_params(settings)
    max_age = max(int((expires_at - datetime.now(UTC)).total_seconds()), 0)
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        httponly=True,
        secure=params["secure"],
        samesite=params["samesite"],
        path=params["path"],
        max_age=max_age or None,
        expires=expires_at,
    )


def set_csrf_cookie(response: JSONResponse, settings, token: str | None = None, expires_at: datetime | None = None):
    """Set CSRF double-submit cookie (non-HttpOnly)."""
    params = cookie_params(settings)
    csrf_value = token or secrets.token_urlsafe(32)
    cookie_kwargs: dict[str, Any] = {
        "key": settings.csrf_cookie_name,
        "value": csrf_value,
        "httponly": False,
        "secure": params["secure"],
        "samesite": params["samesite"],
        "path": params["path"],
    }
    if expires_at:
        cookie_kwargs["expires"] = expires_at
        cookie_kwargs["max_age"] = max(int((expires_at - datetime.now(UTC)).total_seconds()), 0) or None
    response.set_cookie(**cookie_kwargs)


def clear_refresh_cookie(response: JSONResponse, settings) -> None:
    params = cookie_params(settings)
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value="",
        httponly=True,
        secure=params["secure"],
        samesite=params["samesite"],
        path=params["path"],
        max_age=0,
        expires=0,
    )


def clear_csrf_cookie(response: JSONResponse, settings) -> None:
    params = cookie_params(settings)
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value="",
        httponly=False,
        secure=params["secure"],
        samesite=params["samesite"],
        path=params["path"],
        max_age=0,
        expires=0,
    )


def unauthorized_response(detail: str, settings) -> JSONResponse:
    response = json_error_response(status.HTTP_401_UNAUTHORIZED, "unauthorized", detail)
    clear_refresh_cookie(response, settings)
    clear_csrf_cookie(response, settings)
    return response


async def resolve_tenant_or_400(session, identifier: str | None, scope_id=None):
    if not identifier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant identifier is required")
    tenant = await tenant_service.resolve_tenant(session, identifier, scope_id=scope_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is inactive")
    return tenant


def tenant_payload_dict(tenant):
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "is_active": getattr(tenant, "is_active", True),
        "is_soft_launch": is_soft_launch_tenant(tenant.slug),
    }
