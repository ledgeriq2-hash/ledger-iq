from __future__ import annotations

import argparse
import asyncio
from typing import Any

from app.config import get_settings
from app.core.soft_launch import refresh_soft_launch_slugs
from app.database import async_session_maker
from app.initial_data import seed_tenant
from app.services import role_service, tenant_config_service, tenant_service, user_service


async def _ensure_owner_role(session, tenant_id):
    roles = await role_service.list_roles(session, tenant_id)
    for role in roles:
        if role.name.lower() == "owner":
            return role
    return await role_service.create_role(session, tenant_id, {"name": "OWNER", "permissions_json": {"all": True}})


async def onboard(name: str, slug: str, owner_email: str, owner_password: str) -> dict[str, Any]:
    settings = get_settings()
    async with async_session_maker() as session:
        tenant = await tenant_service.resolve_tenant(session, slug, scope_id=None)
        if not tenant:
            tenant = await tenant_service.create_tenant(session, {"name": name, "slug": slug}, scope_id=None)
        await seed_tenant(session, tenant)
        owner_role = await _ensure_owner_role(session, tenant.id)
        existing_user = await user_service.get_user_by_email(session, tenant.id, owner_email)
        if not existing_user:
            owner_payload = {
                "email": owner_email,
                "password": owner_password,
                "full_name": "Pilot Owner",
                "role_id": owner_role.id,
                "is_superuser": True,
            }
            await user_service.create_user(session, tenant.id, owner_payload)
        await tenant_config_service.set_soft_launch(session, tenant.id, True)
    await refresh_soft_launch_slugs()

    login_url = f"{settings.frontend_url}/login?tenant={slug}"
    admin_overview_url = f"{settings.frontend_url}/admin/tenants"
    grafana_url = "http://localhost:3001"  # adjust if deployed elsewhere
    portal_url = f"{settings.frontend_url}/portal"
    return {
        "tenant": {"id": str(tenant.id), "name": name, "slug": slug},
        "owner_email": owner_email,
        "login_url": login_url,
        "portal_url": portal_url,
        "admin_overview_url": admin_overview_url,
        "grafana_url": grafana_url,
        "next_steps": [
            "Ensure Prometheus/Grafana are running (docker-compose.prod.yml).",
            "Verify backups via scripts/backup_db.sh are scheduled.",
            "Share support email with pilot users.",
            "Encourage feedback via in-app 'Send Feedback' button.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Onboard a pilot tenant for soft launch.")
    parser.add_argument("--name", required=True, help="Tenant name")
    parser.add_argument("--slug", required=True, help="Tenant slug")
    parser.add_argument("--email", required=True, help="Owner email")
    parser.add_argument("--password", required=True, help="Owner password")
    args = parser.parse_args()
    result = asyncio.run(onboard(args.name, args.slug, args.email, args.password))
    print("Pilot tenant ready:")
    for key, value in result.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
