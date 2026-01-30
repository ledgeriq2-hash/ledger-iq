from __future__ import annotations

import json
import os
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, EmailStr, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


DEV_DATABASE_URL = "postgresql+asyncpg://ledgeriq:ledgeriq_password@localhost:5432/ledgeriq"
DEV_JWT_SECRET_FALLBACK = "dev-jwt-secret-key"
DEV_JWT_REFRESH_SECRET_FALLBACK = "dev-jwt-refresh-secret-key"


def _resolve_env_file() -> str | None:
    """
    Resolve an explicit env file for local development/test only.

    Production relies solely on process environment variables.
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()
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
        candidate = base_path / ".env.local"
        if candidate.exists():
            return str(candidate)
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
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str | None = None
    redis_enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"
    frontend_url: str = "http://localhost:3000"

    jwt_secret_key: str | None = None
    jwt_refresh_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 30
    refresh_token_expires_days: int = 30
    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_samesite: str = "lax"
    refresh_cookie_path: str = "/"
    refresh_cookie_secure: bool = False
    csrf_enabled: bool = True
    csrf_cookie_name: str = "csrf_token"
    csrf_header_name: str = "X-CSRF-Token"
    csrf_exempt_paths: list[str] = Field(
        default_factory=lambda: [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/billing/webhook",
        ]
    )

    backend_cors_origins: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("BACKEND_CORS_ORIGINS", "CORS_ORIGINS"),
    )
    allow_wildcard_cors: bool = False
    sentry_dsn: str | None = None

    soft_launch_enabled: bool = False
    soft_launch_tenant_slugs: list[str] = Field(default_factory=list)
    show_soft_launch_badge: bool = True
    default_plan_code: str = "free"
    allow_negative_stock: bool = False
    feature_optional_routes: bool = False

    # Rate limiting (requests per window)
    auth_rate_limit_per_minute: int = 60
    portal_rate_limit_per_minute: int = 120
    feedback_rate_limit_per_minute: int = 30

    # Retention (days)
    feedback_retention_days: int = 60
    error_event_retention_days: int = 30
    gdpr_export_ttl_days: int = 7
    gdpr_financial_retention_days: int = 0

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
    billing_enabled: bool = True

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: Any) -> str:
        if value is None or str(value).strip() == "":
            return "INFO"
        return str(value).strip().upper()

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, value: Any) -> str:
        env = str(value or "development").strip().lower()
        allowed = {"development", "staging", "production"}
        if env not in allowed:
            raise ValueError("ENVIRONMENT must be one of: development, staging, production")
        return env

    @field_validator("csrf_enabled", mode="before")
    @classmethod
    def parse_csrf_enabled(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return True
        if isinstance(value, (int, float)):
            return bool(int(value))
        text = str(value).strip().lower()
        if text in {"1", "true", "t", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "f", "no", "n", "off"}:
            return False
        raise ValueError("CSRF_ENABLED must be a boolean (true/false/1/0)")

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

    @model_validator(mode="after")
    def enforce_guardrails(self) -> "Settings":
        """Require critical secrets in production and keep safe defaults elsewhere."""
        env = (self.environment or "development").strip().lower()
        is_production = env in {"production", "staging"}
        if not is_production:
            if not self.database_url or not str(self.database_url).strip():
                object.__setattr__(self, "database_url", DEV_DATABASE_URL)
            if not self.jwt_secret_key:
                object.__setattr__(self, "jwt_secret_key", DEV_JWT_SECRET_FALLBACK)
            if not self.jwt_refresh_secret_key:
                object.__setattr__(self, "jwt_refresh_secret_key", DEV_JWT_REFRESH_SECRET_FALLBACK)
            if not self.backend_cors_origins:
                object.__setattr__(
                    self,
                    "backend_cors_origins",
                    [
                        "http://localhost:5173",
                        "http://127.0.0.1:5173",
                    ],
                )
            return self
        object.__setattr__(self, "refresh_cookie_secure", True)

        missing: list[str] = []
        invalid: list[str] = []

        def require(value: str | None, name: str) -> None:
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(name)

        require(self.jwt_secret_key, "JWT_SECRET_KEY")
        require(self.jwt_refresh_secret_key, "JWT_REFRESH_SECRET_KEY")
        require(self.database_url, "DATABASE_URL")
        if self.database_url and str(self.database_url).strip():
            try:
                driver = make_url(self.database_url).drivername
                if driver.startswith("sqlite"):
                    invalid.append("DATABASE_URL must not use SQLite in production")
            except Exception:
                invalid.append("DATABASE_URL is invalid")
        if self.billing_enabled:
            require(self.stripe_api_key, "STRIPE_API_KEY")
            require(self.stripe_webhook_secret, "STRIPE_WEBHOOK_SECRET")

        if self.backend_cors_origins and "*" in self.backend_cors_origins and not self.allow_wildcard_cors:
            invalid.append("CORS_ORIGINS must not contain '*' in production unless ALLOW_WILDCARD_CORS=true")

        if missing or invalid:
            parts = []
            if missing:
                parts.append(f"missing required env vars: {', '.join(sorted(set(missing)))}")
            if invalid:
                parts.append(f"invalid settings: {', '.join(invalid)}")
            raise ValueError(f"Production configuration error - {'; '.join(parts)}")

        return self


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
