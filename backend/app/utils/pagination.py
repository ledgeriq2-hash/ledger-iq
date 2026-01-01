from __future__ import annotations

from collections.abc import Sequence
from math import ceil
from typing import TypeVar

T = TypeVar("T")
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def normalize_pagination(page: int | None, page_size: int | None, max_page_size: int = MAX_PAGE_SIZE) -> tuple[int, int, int]:
    """Clamp page parameters and return (page, page_size, offset)."""
    page = page or 1
    page_size = page_size or DEFAULT_PAGE_SIZE
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = DEFAULT_PAGE_SIZE
    if page_size > max_page_size:
        page_size = max_page_size
    offset = (page - 1) * page_size
    return page, page_size, offset


def total_pages(total: int, page_size: int) -> int:
    return ceil(total / page_size) if page_size else 0


def paginate(items: Sequence[T], page: int = 1, page_size: int = 50) -> dict:
    if page <= 0:
        page = 1
    if page_size <= 0:
        page_size = 50
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": list(items[start:end]),
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": ceil(total / page_size) if page_size else 0,
    }


__all__ = ["paginate", "normalize_pagination", "total_pages", "DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE"]
