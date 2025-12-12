from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel
from app.schemas.settings import ChartOfAccountsSettings


class Tenant(BaseModel):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    plan: Mapped[str | None] = mapped_column(String(50), nullable=True)
    settings_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_tenants_tenant_id", "tenant_id"),
        Index("ix_tenants_created_at", "created_at"),
        UniqueConstraint("slug", name="uq_tenants_slug"),
    )

    def _settings_dict(self) -> dict[str, Any]:
        """Return settings_json as a mutable dict; fallback to empty dict."""
        return self.settings_json if isinstance(self.settings_json, dict) else {}

    def get_chart_of_accounts_settings(self) -> ChartOfAccountsSettings:
        """
        Safely parse chart of accounts settings from settings_json using the Pydantic schema.

        Priority order:
        1. settings_json["chart_of_accounts_mapping"]
        2. settings_json["accounts"] (legacy)
        3. top-level keys in settings_json (legacy)
        """
        settings = self._settings_dict()
        merged: dict[str, Any] = {}
        for source in (
            settings.get("chart_of_accounts_mapping"),
            settings.get("accounts"),
            settings,
        ):
            if not isinstance(source, dict):
                continue
            for field_name in ChartOfAccountsSettings.model_fields:
                if merged.get(field_name) is not None:
                    continue
                value = source.get(field_name)
                if value is not None:
                    merged[field_name] = value
        return ChartOfAccountsSettings.model_validate(merged)

    @property
    def chart_of_accounts_settings(self) -> ChartOfAccountsSettings:
        """Property wrapper around get_chart_of_accounts_settings for convenience."""
        return self.get_chart_of_accounts_settings()


__all__ = ["Tenant"]
