from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status

from app.api import deps

OWNER = "owner"
ADMIN = "admin"
ACCOUNTANT = "accountant"
VIEWER = "viewer"


def _normalize_roles(raw_roles: Any) -> set[str]:
    normalized: set[str] = set()
    for role in raw_roles:
        if role is None:
            continue
        if isinstance(role, (list, tuple, set, frozenset)):
            normalized.update(_normalize_roles(role))
            continue
        normalized.add(str(role).lower())
    return normalized


def _extract_roles(user: Any) -> set[str]:
    roles: set[str] = set()
    if user is None:
        return roles

    if isinstance(user, dict):
        if "roles" in user:
            roles.update(_normalize_roles(user.get("roles") or []))
        if "role" in user:
            roles.update(_normalize_roles([user.get("role")]))
        return roles

    if hasattr(user, "role"):
        role_value = getattr(user, "role")
        if hasattr(role_value, "name"):
            roles.update(_normalize_roles([getattr(role_value, "name")]))
        roles.update(_normalize_roles([role_value]))
        if hasattr(role_value, "permissions_json"):
            permissions = getattr(role_value, "permissions_json") or {}
            roles.update(_normalize_roles(permissions.get("roles", [])))  # placeholder for future expansions
    if hasattr(user, "roles"):
        roles.update(_normalize_roles(getattr(user, "roles")))
    return roles


def require_roles(roles: list[str]):
    """
    Dependency to enforce role-based access control.

    Usage:
        @router.get(..., dependencies=[Depends(require_roles([OWNER, ADMIN]))])
    """

    if not roles:
        raise ValueError("roles must contain at least one role")

    required = {role.lower() for role in roles}

    async def dependency(current_user=Depends(deps.get_current_user)):
        """
        Future: extend to granular, module-level permissions (e.g., role.permissions_json flags).
        """
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        user_roles = _extract_roles(current_user)
        if hasattr(current_user, "is_active") and not getattr(current_user, "is_active"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
        if not user_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        if required.isdisjoint(user_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


__all__ = ["OWNER", "ADMIN", "ACCOUNTANT", "VIEWER", "require_roles"]
