from __future__ import annotations

import logging

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.rate_limit import enforce_rate_limit
from app.core.redis import bump_user_tokens_version
from app.core.soft_launch import is_soft_launch_tenant
from app.models.user import User
from app.schemas.auth import RefreshRequest, Token
from app.schemas.common import BaseSchema
from app.schemas.role import RolePublic
from app.schemas.tenant import TenantPublic
from app.schemas.user import UserPublic
from app.use_cases.auth.common import (
    clear_csrf_cookie,
    clear_refresh_cookie,
    resolve_tenant_or_400,
    set_csrf_cookie,
    set_refresh_cookie,
    unauthorized_response,
)
from app.use_cases.auth.login import login_user
from app.use_cases.auth.logout import logout_session
from app.use_cases.auth.password_reset import perform_password_reset, request_password_reset
from app.use_cases.auth.refresh import refresh_session
from app.use_cases.auth.register import register_tenant_admin
from app.services import tenant_service, user_service

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)


class LoginPayload(BaseSchema):
    email: EmailStr
    password: str
    tenant: str | None = None  # slug or id; headers take precedence when provided
    mfa_code: str | None = None


class RegistrationTenant(BaseSchema):
    name: str
    slug: str
    plan: str | None = None
    settings_json: dict | None = None


class RegistrationAdmin(BaseSchema):
    email: EmailStr
    password: str
    full_name: str | None = None


class RegisterRequest(BaseSchema):
    tenant: RegistrationTenant
    admin: RegistrationAdmin


class AuthSession(BaseSchema):
    tenant: TenantPublic
    user: UserPublic
    tokens: Token


class ForgotPasswordRequest(BaseSchema):
    email: EmailStr
    tenant: str  # slug or id


class ResetPasswordRequest(BaseSchema):
    token: str
    new_password: str


class CurrentUserResponse(BaseSchema):
    user: UserPublic
    tenant: TenantPublic | None = None
    role: RolePublic | None = None


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    """
    Tenant admin onboarding.

    The reset token and role seeding should be wired to email templates in production;
    for now we create a default OWNER role inline so the first user has admin rights.
    """
    await enforce_rate_limit(request, "auth_register", settings.auth_rate_limit_per_minute)
    result = await register_tenant_admin(payload, request, session, settings)
    tokens = result["tokens"]
    response = JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "tenant": result["tenant"],
            "user": result["user"],
            "tokens": tokens.token.model_dump(),
            "soft_launch_badge": result["soft_launch_badge"],
        },
    )
    set_refresh_cookie(response, settings, tokens.refresh_token, tokens.refresh_expires_at)
    set_csrf_cookie(response, settings)
    return response


@router.post("/login")
async def login(
    payload: LoginPayload,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
    x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    x_tenant_slug: str | None = Header(None, alias="X-Tenant-Slug"),
):
    await enforce_rate_limit(request, "auth_login", settings.auth_rate_limit_per_minute)
    tenant_identifier = x_tenant_id or x_tenant_slug or payload.tenant
    result = await login_user(payload, request, session, settings, tenant_identifier)
    if result.response:
        return result.response
    tokens = result.tokens
    tenant_payload = result.tenant_payload
    user_payload = result.user_payload
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "tenant": tenant_payload,
            "user": user_payload,
            "tokens": tokens.token.model_dump() if tokens else None,
            "soft_launch_badge": result.soft_launch_badge,
        },
    )
    if tokens:
        set_refresh_cookie(response, settings, tokens.refresh_token, tokens.refresh_expires_at)
        set_csrf_cookie(response, settings)
    return response


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
    payload: RefreshRequest | None = None,
    refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
):
    await enforce_rate_limit(request, "auth_refresh", settings.auth_rate_limit_per_minute)
    refresh_value = refresh_token_cookie or (payload.refresh_token if payload else None)
    try:
        tokens = await refresh_session(refresh_value, session, settings, request)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return unauthorized_response(str(exc.detail), settings)
        raise
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=tokens.token.model_dump(),
    )
    set_refresh_cookie(response, settings, tokens.refresh_token, tokens.refresh_expires_at)
    set_csrf_cookie(response, settings)
    return response


@router.post("/logout")
async def logout(
    payload: RefreshRequest | None = None,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
    refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
):
    refresh_value = refresh_token_cookie or (payload.refresh_token if payload else None)
    try:
        await logout_session(refresh_value, session, settings)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return unauthorized_response(str(exc.detail), settings)
        raise
    response = JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "Logged out"})
    clear_refresh_cookie(response, settings)
    clear_csrf_cookie(response, settings)
    return response


@router.post("/logout-all")
async def logout_all(
    session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """
    Revoke all sessions for the authenticated user by bumping the token namespace and
    revoking stored refresh tokens.
    """
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant context required")
    await bump_user_tokens_version(current_user.id)
    await user_service.revoke_all_refresh_tokens_for_user(session, current_user.tenant_id, current_user.id)
    return {"detail": "All sessions revoked"}


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    """
    Issue a one-time password reset token and deliver it via email.
    """
    await enforce_rate_limit(request, "auth_forgot_password", settings.auth_rate_limit_per_minute)
    return await request_password_reset(payload, settings, session)


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    await enforce_rate_limit(request, "auth_reset_password", settings.auth_rate_limit_per_minute)
    return await perform_password_reset(payload, settings, session)


@router.get("/me")
async def read_me(
    current_user: User = Depends(deps.get_current_active_user),
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    tenant = None
    if current_user.tenant_id:
        tenant = await tenant_service.get_tenant(session, current_user.tenant_id, scope_id=None)
    role = current_user.role
    tenant_payload = (
        {
            "id": str(tenant.id),
            "name": tenant.name,
            "slug": tenant.slug,
            "plan": tenant.plan,
            "is_active": getattr(tenant, "is_active", True),
            "is_soft_launch": is_soft_launch_tenant(tenant.slug),
        }
        if tenant
        else None
    )
    user_payload = {
        "id": str(current_user.id),
        "tenant_id": str(current_user.tenant_id) if current_user.tenant_id else None,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role_id": str(current_user.role_id) if current_user.role_id else None,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }
    role_payload = (
        {
            "id": str(role.id),
            "name": role.name,
            "permissions_json": role.permissions_json,
        }
        if role
        else None
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "user": user_payload,
            "tenant": tenant_payload,
            "role": role_payload,
            "soft_launch_badge": bool(
                tenant_payload and tenant_payload.get("is_soft_launch") and settings.show_soft_launch_badge
            ),
        },
    )


__all__ = ["router"]
