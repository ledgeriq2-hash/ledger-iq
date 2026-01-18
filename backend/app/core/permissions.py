from __future__ import annotations

from enum import Enum
from typing import Any

from fastapi import Depends, status

from app.api import deps
from app.core.exceptions import AppException

OWNER = "owner"
ADMIN = "admin"
ACCOUNTANT = "accountant"
VIEWER = "viewer"


class PermissionCode(str, Enum):
    COA_VIEW = "coa.view"
    COA_MANAGE = "coa.manage"
    JOURNAL_VIEW = "journal.view"
    JOURNAL_CREATE = "journal.create"
    JOURNAL_UPDATE = "journal.update"
    JOURNAL_DELETE = "journal.delete"
    JOURNAL_MANUAL_CREATE = "journal.manual.create"
    JOURNAL_POST = "journal.post"
    JOURNAL_REVERSE = "journal.reverse"
    PERIOD_LOCK = "period.lock"
    PERIOD_UNLOCK = "period.unlock"


PERMISSION_CATALOG = tuple(code.value for code in PermissionCode)

ROLE_PERMISSION_PRESETS = {
    OWNER: {"all": True},
    ADMIN: {"all": True, "codes": list(PERMISSION_CATALOG)},
    ACCOUNTANT: {"accounting": True},
    VIEWER: {"read_only": True},
}


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
        role_value = user.role
        if hasattr(role_value, "name"):
            roles.update(_normalize_roles([role_value.name]))
        roles.update(_normalize_roles([role_value]))
        if hasattr(role_value, "permissions_json"):
            permissions = role_value.permissions_json or {}
            roles.update(_normalize_roles(permissions.get("roles", [])))  # placeholder for future expansions
    if hasattr(user, "roles"):
        roles.update(_normalize_roles(user.roles))
    return roles


def _normalize_codes(raw_codes: Any) -> set[str]:
    if raw_codes is None:
        return set()
    if isinstance(raw_codes, str):
        return {raw_codes}
    if isinstance(raw_codes, (list, tuple, set, frozenset)):
        return {str(code) for code in raw_codes if code is not None}
    return set()


def _extract_permissions_payload(user: Any) -> dict[str, Any]:
    if user is None:
        return {}
    if isinstance(user, dict):
        permissions = user.get("permissions")
        if isinstance(permissions, dict):
            return permissions
        permissions_json = user.get("permissions_json")
        if isinstance(permissions_json, dict):
            return permissions_json
    if hasattr(user, "permissions_json") and isinstance(user.permissions_json, dict):
        return user.permissions_json
    role = getattr(user, "role", None)
    if role is not None and isinstance(getattr(role, "permissions_json", None), dict):
        return role.permissions_json
    return {}


def _has_permission(user: Any, permission_code: str) -> bool:
    roles = _extract_roles(user)
    if roles.intersection({OWNER, ADMIN}):
        return True

    permissions = _extract_permissions_payload(user)
    if permissions:
        if permissions.get("all") is True:
            return True
        codes = _normalize_codes(permissions.get("codes") or permissions.get("permissions"))
        if permission_code in codes:
            return True
        if permissions.get("accounting") is True and permission_code.startswith(("journal.", "coa.", "period.")):
            return True
        if permissions.get("read_only") is True and permission_code.endswith(".view"):
            return True

    if hasattr(user, "permissions"):
        codes = _normalize_codes(getattr(user, "permissions"))
        if permission_code in codes:
            return True

    return False


def has_permission(user: Any, permission_code: str) -> bool:
    return _has_permission(user, permission_code)


def ensure_permission(user: Any, permission_code: str, *, message: str = "Insufficient permissions") -> None:
    if getattr(user, "is_superuser", False):
        return
    if not _has_permission(user, permission_code):
        raise AppException(
            code="permission_denied",
            message=message,
            http_status=status.HTTP_403_FORBIDDEN,
        )


def require_roles(roles: list[str]):
    """
    Dependency placeholder for role-based access control.

    Usage:
        @router.get(..., dependencies=[Depends(require_roles([OWNER, ADMIN]))])
    """

    if not roles:
        raise ValueError("roles must contain at least one role")

    async def dependency(current_user=Depends(deps.get_current_active_user)):
        if getattr(current_user, "is_superuser", False):
            return current_user
        required = {role.lower() for role in roles}
        current_roles = _extract_roles(current_user)
        if not current_roles.intersection(required):
            raise AppException(
                code="permission_denied",
                message="Insufficient permissions",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return current_user

    return dependency


def require_perm(permission_code: str):
    if not permission_code:
        raise ValueError("permission_code must be provided")

    async def dependency(current_user=Depends(deps.get_current_active_user)):
        if getattr(current_user, "is_superuser", False):
            return current_user
        if not _has_permission(current_user, permission_code):
            raise AppException(
                code="permission_denied",
                message="Insufficient permissions",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return current_user

    return dependency


__all__ = [
    "OWNER",
    "ADMIN",
    "ACCOUNTANT",
    "VIEWER",
    "PermissionCode",
    "PERMISSION_CATALOG",
    "ROLE_PERMISSION_PRESETS",
    "has_permission",
    "ensure_permission",
    "require_roles",
    "require_perm",
]
