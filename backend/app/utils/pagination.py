from __future__ import annotations

from math import ceil
from typing import Iterable, List, Sequence, TypeVar

T = TypeVar("T")


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


__all__ = ["paginate"]
