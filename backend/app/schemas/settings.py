from __future__ import annotations

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


__all__ = ["ChartOfAccountsSettings"]
