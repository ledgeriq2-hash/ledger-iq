from __future__ import annotations

import json
import os
import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Sequence

from pydantic import EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_file() -> str | None:
    """
    Resolve an explicit env file for local development/test only.

    Production relies solely on process environment variables.
    """
    environment = os.getenv("ENVIRONMENT", "production").lower()
    if environment not in {"development", "test"}:
        return None

    explicit_file = os.getenv("ENV_FILE")
    if explicit_file:
        path = Path(explicit_file)
        if path.exists():
            return str(path)

    base_paths = [
        Path(__file__).resolve().parents[3],  # repo root
        Path(__file__).resolve().parents[2],  # backend directory
    ]
    for base_path in base_paths:
        candidate = base_path / f".env.{environment}"
        if candidate.exists():
            return str(candidate)
    return None


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Ledger IQ"
    environment: str = "production"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./ledgeriq.db"
    redis_url: str = "redis://localhost:6379/0"
    frontend_url: str = "http://localhost:3000"

    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_refresh_secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 30
    refresh_token_expires_days: int = 30

    backend_cors_origins: List[str] = Field(default_factory=list)
    sentry_dsn: str | None = None

    soft_launch_enabled: bool = False
    soft_launch_tenant_slugs: List[str] = Field(default_factory=list)
    show_soft_launch_badge: bool = True
    default_plan_code: str = "free"
    allow_negative_stock: bool = False

    # Rate limiting (requests per window)
    auth_rate_limit_per_minute: int = 60
    portal_rate_limit_per_minute: int = 120
    feedback_rate_limit_per_minute: int = 30

    # Retention (days)
    feedback_retention_days: int = 60
    error_event_retention_days: int = 30

    email_host: str | None = None
    email_port: int = 587
    email_user: str | None = None
    email_password: str | None = None
    email_from: EmailStr | None = None
    email_tls: bool = True
    email_ssl: bool = False

    # Billing / Stripe
    stripe_api_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_free: str | None = None
    stripe_price_pro: str | None = None

    @field_validator("soft_launch_tenant_slugs", mode="before")
    @classmethod
    def split_soft_launch_slugs(cls, value: Any) -> list[str]:
        """Allow soft-launch tenant slugs to be provided as JSON array or comma-separated string."""
        if value is None:
            return []
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return []
            if candidate.startswith("["):
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                    raise ValueError("Invalid JSON for soft launch tenant slugs") from exc
                if not isinstance(parsed, Sequence):
                    raise ValueError("Soft launch tenants JSON must be a sequence")
                return [str(slug).strip() for slug in parsed if str(slug).strip()]
            return [slug.strip() for slug in candidate.split(",") if slug.strip()]
        if isinstance(value, (list, tuple, set, frozenset)):
            return [str(slug).strip() for slug in value if str(slug).strip()]
        raise ValueError("Unsupported type for soft launch tenant slugs")

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: Any) -> list[str]:
        """Allow CORS origins to be provided as JSON array or comma-separated string."""
        if value is None:
            return []
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return []
            if candidate.startswith("["):
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                    raise ValueError("Invalid JSON for CORS origins") from exc
                if not isinstance(parsed, Sequence):
                    raise ValueError("CORS origins JSON must be a sequence")
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
            return [origin.strip() for origin in candidate.split(",") if origin.strip()]
        if isinstance(value, (list, tuple, set, frozenset)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        raise ValueError("Unsupported type for CORS origins")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    env_file = _resolve_env_file()
    init_kwargs: dict[str, Any] = {}
    if env_file:
        init_kwargs["_env_file"] = env_file
        init_kwargs["_env_file_encoding"] = "utf-8"
    return Settings(**init_kwargs)


__all__ = ["Settings", "get_settings"]
