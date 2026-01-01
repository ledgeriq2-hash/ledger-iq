from __future__ import annotations

from app.schemas.common import BaseSchema, IDTimestampMixin


class RoleBase(BaseSchema):
    name: str
    permissions_json: dict | None = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseSchema):
    name: str | None = None
    permissions_json: dict | None = None


class RolePublic(IDTimestampMixin, RoleBase):
    pass


class RoleList(BaseSchema):
    items: list[RolePublic]
    page: int = 1
    page_size: int = 25
    total: int = 0
    pages: int = 0


__all__ = ["RoleBase", "RoleCreate", "RoleUpdate", "RolePublic", "RoleList"]
