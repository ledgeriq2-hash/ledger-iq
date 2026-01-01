from __future__ import annotations

from app.schemas.common import BaseSchema


class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    expires_in: int | None = None


class TokenPayload(BaseSchema):
    sub: str | None = None
    exp: int | None = None
    jti: str | None = None


class LoginRequest(BaseSchema):
    email: str
    password: str


class RefreshRequest(BaseSchema):
    refresh_token: str | None = None


__all__ = ["Token", "TokenPayload", "LoginRequest", "RefreshRequest"]
