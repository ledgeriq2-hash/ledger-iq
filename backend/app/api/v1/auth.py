from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.exceptions import AppException
from app.core.rate_limit import enforce_rate_limit
from app.core.redis import (
    bump_user_tokens_version,
    get_user_tokens_version,
    is_token_revoked,
    pop_password_reset_token,
    set_password_reset_token,
    store_token_jti,
)
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.core.soft_launch import is_soft_launch_tenant
from app.models.user import User
from app.schemas.auth import RefreshRequest, Token
from app.schemas.common import BaseSchema
from app.schemas.role import RolePublic
from app.schemas.tenant import TenantPublic
from app.schemas.user import UserPublic
from app.services import (
    audit_log_service,
    email_service,
    role_service,
    tenant_service,
    usage_service,
    user_service,
)

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


def _exp_to_datetime(exp_value: int | datetime | None, fallback_seconds: int) -> datetime:
    if isinstance(exp_value, datetime):
        return exp_value if exp_value.tzinfo else exp_value.replace(tzinfo=UTC)
    try:
        exp_int = int(exp_value) if exp_value is not None else None
    except (TypeError, ValueError):
        exp_int = None
    if exp_int:
        return datetime.fromtimestamp(exp_int, tz=UTC)
    return datetime.now(UTC) + timedelta(seconds=fallback_seconds)


def _build_claims(user: User, tenant_id: uuid.UUID, token_version: int) -> dict[str, object]:
    role_name = user.role.name if user.role else (str(user.role_id) if user.role_id else None)
    permissions = user.role.permissions_json if user.role else None
    return {
        "tenant_id": str(tenant_id),
        "role": role_name,
        "permissions": permissions or [],
        "token_version": token_version,
    }


async def _issue_token_pair(
    session: AsyncSession, settings, user: User, tenant_id: uuid.UUID, token_version: int, *, request: Request | None
) -> Token:
    claims = _build_claims(user, tenant_id, token_version)
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
    refresh_exp = _exp_to_datetime(
        refresh_payload.get("exp"),
        fallback_seconds=settings.refresh_token_expires_days * 24 * 60 * 60,
    )
    user_agent = request.headers.get("User-Agent") if request else None
    ip_address = request.client.host if request and request.client else None
    await user_service.store_refresh_token(
        session, tenant_id, user.id, refresh_token, refresh_exp, user_agent=user_agent, ip_address=ip_address
    )
    return Token(access_token=access_token, refresh_token=refresh_token)


async def _resolve_tenant_or_400(session: AsyncSession, identifier: str | None) -> uuid.UUID:
    if not identifier:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant identifier is required")
    tenant = await tenant_service.resolve_tenant(session, identifier, scope_id=None)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant is inactive")
    return tenant.id


def _ensure_refresh_token_type(decoded: dict[str, object]) -> None:
    token_type = decoded.get("type")
    if token_type not in (None, "refresh"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token type")


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
    tenant = await tenant_service.create_tenant(session, payload.tenant, scope_id=None)
    owner_role = await role_service.create_role(
        session,
        tenant.id,
        {"name": "OWNER", "permissions_json": {"all": True}},
    )
    admin_payload = payload.admin.model_dump()
    admin_payload["role_id"] = owner_role.id
    admin_payload["is_superuser"] = True

    admin_user = await user_service.create_user(session, tenant.id, admin_payload)
    admin_user.role = owner_role
    token_version = await get_user_tokens_version(admin_user.id)
    tokens = await _issue_token_pair(session, settings, admin_user, tenant.id, token_version, request=request)
    await user_service.set_last_login(session, tenant.id, admin_user.id)

    tenant_payload = {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "is_active": getattr(tenant, "is_active", True),
        "is_soft_launch": is_soft_launch_tenant(tenant.slug),
    }
    user_payload = {
        "id": str(admin_user.id),
        "tenant_id": str(tenant.id),
        "email": admin_user.email,
        "full_name": admin_user.full_name,
        "role_id": str(admin_user.role_id) if admin_user.role_id else None,
        "is_active": admin_user.is_active,
        "is_superuser": admin_user.is_superuser,
        "last_login_at": admin_user.last_login_at.isoformat() if admin_user.last_login_at else None,
    }
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "tenant": tenant_payload,
            "user": user_payload,
            "tokens": tokens.model_dump(),
            "soft_launch_badge": settings.show_soft_launch_badge and is_soft_launch_tenant(tenant.slug),
        },
    )


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
    tenant_id = await _resolve_tenant_or_400(session, tenant_identifier)

    user = await user_service.authenticate_user(session, tenant_id, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # MFA gate: issue challenge and short-circuit until verified
    if getattr(user, "mfa_enabled", False):
        redis = await deps.get_redis()
        mfa_key = f"mfa:{user.id}"
        cached = await redis.get(mfa_key)
        if payload.mfa_code:
            if not cached or cached.decode() != payload.mfa_code:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
            await redis.delete(mfa_key)
        else:
            code = secrets.token_hex(3)
            await redis.set(mfa_key, code, ex=300)
            if user.email:
                try:
                    await email_service.send_email(
                        to=user.email,
                        subject=f"{settings.app_name} verification code",
                        body_text=f"Your verification code is {code}",
                        body_html=f"<p>Your verification code is <strong>{code}</strong></p>",
                        settings=settings,
                    )
                except Exception:
                    pass
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={"mfa_required": True, "detail": "Verification code sent"},
            )

    token_version = await get_user_tokens_version(user.id)
    tokens = await _issue_token_pair(session, settings, user, tenant_id, token_version, request=request)
    try:
        await audit_log_service.record_audit_log(
            session,
            tenant_id=tenant_id,
            table_name="users",
            record_id=str(user.id),
            action="login",
            user_id=user.id,
        )
    except Exception:
        pass
    await user_service.set_last_login(session, tenant_id, user.id)
    await usage_service.record_login(session, tenant_id)

    tenant = await tenant_service.get_tenant(session, tenant_id, scope_id=None)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    tenant_soft_launch = is_soft_launch_tenant(tenant.slug)
    tenant_payload = {
        "id": str(tenant.id),
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
        "is_active": getattr(tenant, "is_active", True),
        "is_soft_launch": tenant_soft_launch,
    }
    user_payload = {
        "id": str(user.id),
        "tenant_id": str(tenant.id),
        "email": user.email,
        "full_name": user.full_name,
        "role_id": str(user.role_id) if user.role_id else None,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "tenant": tenant_payload,
            "user": user_payload,
            "tokens": tokens.model_dump(),
            "soft_launch_badge": settings.show_soft_launch_badge and tenant_soft_launch,
        },
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
    payload: RefreshRequest | None = None,
    refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
):
    await enforce_rate_limit(request, "auth_refresh", settings.auth_rate_limit_per_minute)
    refresh_value = (payload.refresh_token if payload else None) or refresh_token_cookie
    if not refresh_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token required")
    try:
        decoded = decode_token(refresh_value, refresh=True)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    _ensure_refresh_token_type(decoded)
    if not decoded.get("jti"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    sub = decoded.get("sub")
    tenant_id = decoded.get("tenant_id")
    if not sub or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    try:
        user_id = uuid.UUID(str(sub))
        tenant_uuid = uuid.UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims") from exc

    if await is_token_revoked(decoded.get("jti")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    token_version_claim = int(decoded.get("token_version") or 0)
    current_version = await get_user_tokens_version(user_id)
    if token_version_claim < current_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is no longer valid")

    user = await user_service.get_user(session, tenant_uuid, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    db_token = await user_service.get_valid_refresh_token(session, tenant_uuid, user_id, refresh_value)
    if not db_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")

    await user_service.revoke_refresh_token(session, tenant_uuid, refresh_value, user_id)
    jti = decoded.get("jti")
    if jti:
        await store_token_jti(
            str(jti),
            _exp_to_datetime(decoded.get("exp"), settings.refresh_token_expires_days * 24 * 60 * 60),
        )

    tokens = await _issue_token_pair(
        session,
        settings,
        user,
        tenant_uuid,
        token_version=max(current_version, token_version_claim),
        request=request,
    )
    return tokens


@router.post("/logout")
async def logout(
    payload: RefreshRequest | None = None,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
    refresh_token_cookie: str | None = Cookie(None, alias="refresh_token"),
):
    refresh_value = (payload.refresh_token if payload else None) or refresh_token_cookie
    if not refresh_value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Refresh token required")
    try:
        decoded = decode_token(refresh_value, refresh=True)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    _ensure_refresh_token_type(decoded)
    if not decoded.get("jti"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    sub = decoded.get("sub")
    tenant_id = decoded.get("tenant_id")
    if not tenant_id or not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    try:
        user_uuid = uuid.UUID(str(sub))
        tenant_uuid = uuid.UUID(str(tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims") from exc

    await user_service.revoke_refresh_token(session, tenant_uuid, refresh_value, user_uuid)
    jti = decoded.get("jti")
    if jti:
        await store_token_jti(
            str(jti),
            _exp_to_datetime(decoded.get("exp"), settings.refresh_token_expires_days * 24 * 60 * 60),
        )
    try:
        await audit_log_service.record_audit_log(
            session,
            tenant_id=tenant_uuid,
            table_name="users",
            record_id=str(user_uuid),
            action="logout",
            user_id=user_uuid,
        )
    except Exception:
        pass
    return {"detail": "Logged out"}


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
    tenant_id = await _resolve_tenant_or_400(session, payload.tenant)
    user = await user_service.get_user_by_email(session, tenant_id, payload.email)
    if not user or not user.is_active:
        raise AppException(code="user_not_found", message="User not found", http_status=status.HTTP_404_NOT_FOUND)

    reset_token = secrets.token_urlsafe(48)
    expires_in_seconds = settings.access_token_expires_minutes * 60  # short-lived reset token
    await set_password_reset_token(reset_token, user.id, tenant_id, expires_in_seconds)

    reset_link = email_service.build_frontend_url(
        f"reset-password?token={reset_token}&tenant={tenant_id}",
        settings=settings,
    )
    subject = f"{settings.app_name} password reset"
    body_text = f"Use the link to reset your password (expires in {settings.access_token_expires_minutes} minutes): {reset_link}"
    body_html = (
        f"<p>Use the link below to reset your password. It expires in "
        f"{settings.access_token_expires_minutes} minutes.</p>"
        f'<p><a href="{reset_link}">{reset_link}</a></p>'
    )
    try:
        await email_service.send_email(
            to=user.email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            settings=settings,
        )
    except Exception as exc:  # pragma: no cover - external dependency path
        logger.exception("Failed to send reset email for user %s", user.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send reset email") from exc

    response = {"detail": "Password reset email sent"}
    if settings.debug:
        response["reset_token"] = reset_token
        response["reset_link"] = reset_link
    return response


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(deps.get_db),
    settings=Depends(deps.get_settings),
):
    await enforce_rate_limit(request, "auth_reset_password", settings.auth_rate_limit_per_minute)
    token_data = await pop_password_reset_token(payload.token)
    if not token_data:
        raise AppException(code="invalid_reset_token", message="Invalid or expired reset token", http_status=status.HTTP_400_BAD_REQUEST)
    user_id, tenant_id = token_data

    user = await user_service.update_user_password(session, tenant_id, user_id, payload.new_password)
    if not user or not user.is_active:
        raise AppException(code="user_not_found", message="User not found or inactive", http_status=status.HTTP_404_NOT_FOUND)

    await bump_user_tokens_version(user_id)
    await user_service.revoke_all_refresh_tokens_for_user(session, tenant_id, user_id)
    return {"detail": "Password reset successful"}


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
