from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import BaseSchema


class ChartOfAccountsSettings(BaseSchema):
    """
    Tenant-level chart of accounts mapping stored under settings_json['chart_of_accounts_mapping'].
    All fields are optional but validated to be UUIDs when present.
    """

    accounts_receivable_account_id: UUID | None = Field(default=None)
    revenue_account_id: UUID | None = Field(default=None)
    expense_account_id: UUID | None = Field(default=None)
    cash_account_id: UUID | None = Field(default=None)
    bank_account_id: UUID | None = Field(default=None)
    payables_account_id: UUID | None = Field(default=None)

    @field_validator("*", mode="before")
    @classmethod
    def _coerce_uuid(cls, value: object) -> UUID | None:
        """
        Accept UUIDs or UUID-like strings; treat blanks as missing.
        Raises a validation error for invalid UUID formats.
        """
        if value is None or value == "":
            return None
        if isinstance(value, UUID):
            return value
        try:
            return UUID(str(value))
        except Exception as exc:  # noqa: BLE001
            raise ValueError("must be a valid UUID") from exc


class AppSettings(BaseSchema):
    feature_toggles: dict[str, Any] = Field(default_factory=dict)
    currency: str = Field(default="USD")
    taxes: dict[str, Any] = Field(default_factory=dict)
    field_labels: dict[str, str] = Field(default_factory=dict)
    theme: dict[str, Any] = Field(default_factory=dict)


class AppSettingsUpdate(BaseSchema):
    feature_toggles: dict[str, Any] | None = None
    currency: str | None = None
    taxes: dict[str, Any] | None = None
    field_labels: dict[str, str] | None = None
    theme: dict[str, Any] | None = None


__all__ = ["ChartOfAccountsSettings", "AppSettings", "AppSettingsUpdate"]
