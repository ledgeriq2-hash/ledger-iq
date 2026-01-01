from __future__ import annotations

from collections.abc import Iterable
from math import ceil
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    @field_validator("page")
    @classmethod
    def _page_positive(cls, value: int) -> int:
        return max(1, value)

    @field_validator("page_size")
    @classmethod
    def _page_size_clamped(cls, value: int) -> int:
        if value <= 0:
            return DEFAULT_PAGE_SIZE
        return min(value, MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    pages: int

    @classmethod
    def from_results(
        cls,
        *,
        items: Iterable[T],
        total: int,
        params: PaginationParams,
    ) -> "PaginatedResponse[T]":
        page_size = params.page_size
        pages = ceil(total / page_size) if page_size else 0
        return cls(
            items=list(items),
            page=params.page,
            page_size=page_size,
            total=total,
            pages=pages,
        )


def pagination_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


async def paginate_query(
    session: AsyncSession,
    statement: Select,
    params: PaginationParams,
) -> tuple[list, int]:
    subquery = statement.order_by(None).subquery()
    total_result = await session.execute(select(func.count()).select_from(subquery))
    total = int(total_result.scalar_one() or 0)
    result = await session.execute(statement.offset(params.offset).limit(params.page_size))
    return list(result.scalars().all()), total


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "PaginationParams",
    "PaginatedResponse",
    "pagination_params",
    "paginate_query",
]
