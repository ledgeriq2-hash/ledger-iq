from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import store_token_jti
from app.core.security import decode_token
from app.use_cases.auth.common import ensure_refresh_token_type, exp_to_datetime
from app.services import audit_log_service, user_service


async def logout_session(refresh_value: str, session: AsyncSession, settings) -> None:
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
            exp_to_datetime(decoded.get("exp"), settings.refresh_token_expires_days * 24 * 60 * 60),
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

