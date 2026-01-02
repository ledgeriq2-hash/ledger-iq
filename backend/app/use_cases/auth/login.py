from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.redis import get_user_tokens_version
from app.use_cases.auth.common import IssuedTokens, issue_token_pair, resolve_tenant_or_400, tenant_payload_dict
from app.services import (
    audit_log_service,
    email_service,
    usage_service,
    user_service,
)


@dataclass
class LoginResult:
    tokens: IssuedTokens | None
    tenant_payload: dict | None
    user_payload: dict | None
    soft_launch_badge: bool
    response: JSONResponse | None = None


async def _handle_mfa(user, request, settings, mfa_code: str | None) -> JSONResponse | None:
    redis = await deps.get_redis()
    mfa_key = f"mfa:{user.id}"
    cached = await redis.get(mfa_key)
    if mfa_code:
        if not cached or cached.decode() != mfa_code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA code")
        await redis.delete(mfa_key)
        return None
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


async def login_user(
    payload,
    request,
    session: AsyncSession,
    settings,
    tenant_identifier: str | None,
) -> LoginResult:
    tenant = await resolve_tenant_or_400(session, tenant_identifier, scope_id=None)

    user = await user_service.authenticate_user(session, tenant.id, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if getattr(user, "mfa_enabled", False):
        pending_response = await _handle_mfa(user, request, settings, payload.mfa_code)
        if pending_response:
            return LoginResult(tokens=None, tenant_payload=None, user_payload=None, soft_launch_badge=False, response=pending_response)

    token_version = await get_user_tokens_version(user.id)
    tokens = await issue_token_pair(session, settings, user, tenant.id, token_version, request=request)
    try:
        await audit_log_service.record_audit_log(
            session,
            tenant_id=tenant.id,
            table_name="users",
            record_id=str(user.id),
            action="login",
            user_id=user.id,
        )
    except Exception:
        pass
    await user_service.set_last_login(session, tenant.id, user.id)
    await usage_service.record_login(session, tenant.id)

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
    tenant_payload = tenant_payload_dict(tenant)

    return LoginResult(
        tokens=tokens,
        tenant_payload=tenant_payload,
        user_payload=user_payload,
        soft_launch_badge=settings.show_soft_launch_badge and tenant_payload.get("is_soft_launch", False),
    )
