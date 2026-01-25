from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import field_validator

from app.schemas.common import BaseSchema


class AiRunMetaV1(BaseSchema):
    model_name: str
    model_version: str
    dataset_fingerprint: str
    created_at: datetime
    created_by: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    scenario: str = "baseline"


class AiRunCreateRequest(BaseSchema):
    schema_version: str
    run_meta: AiRunMetaV1
    payload: dict[str, Any]
    signature: str | None = None

    @field_validator("schema_version")
    @classmethod
    def schema_version_must_be_v1(cls, value: str) -> str:
        if value != "1.0":
            raise ValueError("schema_version must be '1.0'")
        return value

    @field_validator("payload", mode="before")
    @classmethod
    def payload_must_be_object(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("payload must be a JSON object")
        if not value:
            raise ValueError("payload must not be empty")
        return value


class AiRunResponse(BaseSchema):
    id: UUID
    client_id: UUID
    schema_version: str
    run_meta: AiRunMetaV1
    status: str
    payload_hash: str
    payload_json: dict[str, Any]
    signature: str | None = None
    created_at: datetime
    created_by: str | None = None
    revoked_at: datetime | None = None
    revoked_by: str | None = None
    revoke_reason: str | None = None
    superseded_by_run_id: UUID | None = None


__all__ = ["AiRunMetaV1", "AiRunCreateRequest", "AiRunResponse"]
