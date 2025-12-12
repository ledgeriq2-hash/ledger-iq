from __future__ import annotations

from pydantic import field_validator

from app.schemas.common import BaseSchema, IDTimestampMixin


class TenantBase(BaseSchema):
    name: str
    slug: str
    is_active: bool = True
    plan: str | None = None
    settings_json: dict | None = None
    is_soft_launch: bool | None = None

    @field_validator("name", "slug")
    @classmethod
    def not_blank(cls, v: str) -> str:
        value = (v or "").strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseSchema):
    name: str | None = None
    slug: str | None = None
    is_active: bool | None = None
    plan: str | None = None
    settings_json: dict | None = None


class TenantPublic(IDTimestampMixin, TenantBase):
    pass


__all__ = ["TenantBase", "TenantCreate", "TenantUpdate", "TenantPublic"]
