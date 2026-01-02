from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_user_tokens_version
from app.core.soft_launch import is_soft_launch_tenant
from app.schemas.auth import Token
from app.use_cases.auth.common import IssuedTokens, issue_token_pair, tenant_payload_dict
from app.services import (
    audit_log_service,
    role_service,
    tenant_service,
    usage_service,
    user_service,
)


async def register_tenant_admin(payload, request, session: AsyncSession, settings) -> dict:
    """
    Create tenant + admin user, seed owner role, and return token bundle with payloads.
    """
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
    tokens: IssuedTokens = await issue_token_pair(session, settings, admin_user, tenant.id, token_version, request=request)
    await user_service.set_last_login(session, tenant.id, admin_user.id)

    tenant_payload = tenant_payload_dict(tenant)
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

    try:
        await audit_log_service.record_audit_log(
            session,
            tenant_id=tenant.id,
            table_name="users",
            record_id=str(admin_user.id),
            action="register",
            user_id=admin_user.id,
        )
    except Exception:
        pass

    await usage_service.record_login(session, tenant.id)

    return {
        "tenant": tenant_payload,
        "user": user_payload,
        "tokens": tokens,
        "soft_launch_badge": settings.show_soft_launch_badge and is_soft_launch_tenant(tenant.slug),
    }

