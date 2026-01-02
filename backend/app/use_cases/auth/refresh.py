from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_user_tokens_version, is_token_revoked, store_token_jti
from app.core.security import decode_token
from app.use_cases.auth.common import IssuedTokens, ensure_refresh_token_type, exp_to_datetime, issue_token_pair
from app.services import user_service


async def refresh_session(
    refresh_value: str,
    session: AsyncSession,
    settings,
    request,
) -> IssuedTokens:
    if not refresh_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")
    try:
        decoded = decode_token(refresh_value, refresh=True)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    try:
        ensure_refresh_token_type(decoded)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

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
            exp_to_datetime(decoded.get("exp"), settings.refresh_token_expires_days * 24 * 60 * 60),
        )

    return await issue_token_pair(
        session,
        settings,
        user,
        tenant_uuid,
        token_version=max(current_version, token_version_claim),
        request=request,
    )

