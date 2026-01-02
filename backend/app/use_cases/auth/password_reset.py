from __future__ import annotations

import secrets

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import bump_user_tokens_version, pop_password_reset_token, set_password_reset_token
from app.services import email_service, user_service
from app.use_cases.auth.common import resolve_tenant_or_400


async def request_password_reset(payload, settings, session: AsyncSession) -> dict:
    tenant = await resolve_tenant_or_400(session, payload.tenant)
    user = await user_service.get_user_by_email(session, tenant.id, payload.email)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    reset_token = secrets.token_urlsafe(48)
    expires_in_seconds = settings.access_token_expires_minutes * 60
    await set_password_reset_token(reset_token, user.id, tenant.id, expires_in_seconds)

    reset_link = email_service.build_frontend_url(
        f"reset-password?token={reset_token}&tenant={tenant.id}",
        settings=settings,
    )
    subject = f"{settings.app_name} password reset"
    body_text = (
        f"Use the link to reset your password (expires in {settings.access_token_expires_minutes} minutes): {reset_link}"
    )
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
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send reset email"
        ) from exc

    response = {"detail": "Password reset email sent"}
    if settings.debug:
        response["reset_token"] = reset_token
        response["reset_link"] = reset_link
    return response


async def perform_password_reset(payload, settings, session: AsyncSession) -> dict:
    token_data = await pop_password_reset_token(payload.token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        )
    user_id, tenant_id = token_data

    user = await user_service.update_user_password(session, tenant_id, user_id, payload.new_password)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or inactive")

    await bump_user_tokens_version(user_id)
    await user_service.revoke_all_refresh_tokens_for_user(session, tenant_id, user_id)
    return {"detail": "Password reset successful"}
