from __future__ import annotations

from uuid import UUID

from app.schemas.common import BaseSchema, IDTimestampMixin


class AccountBase(BaseSchema):
    code: str
    name: str
    type: str
    normal_balance: str
    parent_id: UUID | None = None
    is_system: bool = False
    is_active: bool = True


class AccountCreate(BaseSchema):
    code: str
    name: str
    type: str
    normal_balance: str
    parent_id: UUID | None = None


class AccountUpdate(BaseSchema):
    name: str | None = None
    type: str | None = None
    normal_balance: str | None = None
    parent_id: UUID | None = None
    is_active: bool | None = None


class AccountPublic(IDTimestampMixin, AccountBase):
    pass


class AccountList(BaseSchema):
    items: list[AccountPublic]


class AccountMappingBase(BaseSchema):
    key: str
    account_id: UUID


class AccountMappingCreate(AccountMappingBase):
    pass


class AccountMappingPublic(IDTimestampMixin, AccountMappingBase):
    pass


class AccountMappingList(BaseSchema):
    items: list[AccountMappingPublic]


__all__ = [
    "AccountBase",
    "AccountCreate",
    "AccountUpdate",
    "AccountPublic",
    "AccountList",
    "AccountMappingBase",
    "AccountMappingCreate",
    "AccountMappingPublic",
    "AccountMappingList",
]
