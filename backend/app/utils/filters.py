from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any


def apply_filters(
    items: Iterable[Mapping[str, Any]],
    filters: Mapping[str, Any] | None = None,
    comparator: Callable[[Any, Any], bool] | None = None,
) -> list[Mapping[str, Any]]:
    """
    Filter an iterable of mappings by key/value pairs.

    comparator: function(value, target) -> bool
    """
    if not filters:
        return list(items)

    def default_compare(value: Any, target: Any) -> bool:
        return value == target

    compare = comparator or default_compare
    result = []
    for item in items:
        if all(compare(item.get(key), target) for key, target in filters.items()):
            result.append(item)
    return result


__all__ = ["apply_filters"]
