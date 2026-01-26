from __future__ import annotations

import argparse
import asyncio
import uuid

from app.config import get_settings
from app.core.redis import get_user_tokens_version
from app.core.security import create_access_token
from app.database import async_session_maker
from app.services import tenant_service, user_service
from app.use_cases.auth.common import build_claims


def _mask_token(token: str) -> str:
    if len(token) <= 14:
        return "***"
    return f"{token[:8]}...{token[-6:]}"


async def _issue_token(tenant_id: uuid.UUID, email: str, expires_minutes: int | None) -> str:
    async with async_session_maker() as session:
        tenant = await tenant_service.get_tenant(session, tenant_id, scope_id=None)
        if not tenant:
            raise RuntimeError(f"Tenant not found: {tenant_id}")

        user = await user_service.get_user_by_email(session, tenant_id, email)
        if not user:
            raise RuntimeError(f"User not found for tenant: {email}")
        if not user.is_active:
            raise RuntimeError("User is inactive")

        token_version = await get_user_tokens_version(user.id)
        claims = build_claims(user, tenant_id, token_version)
        settings = get_settings()
        minutes = expires_minutes if expires_minutes is not None else settings.access_token_expires_minutes
        return create_access_token(subject=str(user.id), claims=claims, expires_minutes=minutes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue a local test JWT for an existing user.")
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--expires-minutes", type=int, default=None, help="Override token expiry minutes")
    parser.add_argument(
        "--print-full",
        action="store_true",
        help="Print full token in export commands (default: redacted)",
    )
    args = parser.parse_args()

    try:
        tenant_id = uuid.UUID(str(args.tenant_id))
    except ValueError as exc:
        raise SystemExit(f"Invalid tenant id: {args.tenant_id}") from exc

    try:
        token = asyncio.run(_issue_token(tenant_id, args.email, args.expires_minutes))
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    masked = _mask_token(token)
    token_value = token if args.print_full else "<redacted>"
    print(f"Token (masked): {masked}")
    print(f'$env:AI_TEST_JWT="{token_value}"')
    print(f'$env:AI_TEST_TENANT_ID="{tenant_id}"')
    print(f'export AI_TEST_JWT="{token_value}"')
    print(f'export AI_TEST_TENANT_ID="{tenant_id}"')
    if not args.print_full:
        print("Use --print-full to output full token for export commands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
