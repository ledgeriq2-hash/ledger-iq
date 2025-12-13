from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()
pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False,
)


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def enforce_password_policy(password: str) -> None:
    """
    Basic password policy: length >= 8, at least one upper, one lower, one digit.

    Raises ValueError on failure.
    """
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if password.lower() == password or password.upper() == password:
        raise ValueError("Password must include upper and lower case letters")
    if not any(ch.isdigit() for ch in password):
        raise ValueError("Password must include at least one digit")


def _create_token(
    subject: str | int,
    expires_delta: timedelta,
    secret_key: str,
    algorithm: str,
    additional_claims: dict[str, Any] | None = None,
    token_use: str | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid.uuid4()),
    }
    if token_use:
        payload["type"] = token_use
    if additional_claims:
        payload.update(additional_claims)
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def create_access_token(
    subject: str | int,
    expires_minutes: int | None = None,
    claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token."""
    minutes = expires_minutes if expires_minutes is not None else settings.access_token_expires_minutes
    expires_delta = timedelta(minutes=minutes)
    return _create_token(
        subject=subject,
        expires_delta=expires_delta,
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        additional_claims=claims,
        token_use="access",
    )


def create_refresh_token(
    subject: str | int,
    expires_days: int | None = None,
    claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT refresh token."""
    days = expires_days if expires_days is not None else settings.refresh_token_expires_days
    expires_delta = timedelta(days=days)
    return _create_token(
        subject=subject,
        expires_delta=expires_delta,
        secret_key=settings.jwt_refresh_secret_key,
        algorithm=settings.jwt_algorithm,
        additional_claims=claims,
        token_use="refresh",
    )


def decode_token(
    token: str,
    *,
    refresh: bool = False,
    options: dict[str, Any] | None = None,
    secret_key: str | None = None,
) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    The secret can be overridden for one-off tokens (e.g., password reset) by
    providing ``secret_key``. Otherwise refresh/access keys are used.
    """
    key = secret_key or (settings.jwt_refresh_secret_key if refresh else settings.jwt_secret_key)
    try:
        decoded = jwt.decode(token, key, algorithms=[settings.jwt_algorithm], options=options or {})
        if refresh and not decoded.get("jti"):
            raise ValueError("Refresh token missing jti")
        return decoded
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


__all__ = [
    "get_password_hash",
    "verify_password",
    "enforce_password_policy",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "pwd_context",
]
