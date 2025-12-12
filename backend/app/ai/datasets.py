from __future__ import annotations

from typing import Any, Iterable, List

from app.ai.utils import to_float_series


def load_revenue_series(payload: Any) -> list[float]:
    """
    Extract a revenue time series from arbitrary payloads.

    Expected formats:
    - {"revenues": [..]}
    - {"data": [{"value": ..}, ...]}
    - A raw list/iterable of numbers
    """
    if payload is None:
        return []

    if isinstance(payload, dict):
        if "revenues" in payload:
            return to_float_series(payload["revenues"])
        if "data" in payload and isinstance(payload["data"], Iterable):
            return to_float_series([item.get("value") for item in payload["data"] if isinstance(item, dict)])
    if isinstance(payload, Iterable):
        return to_float_series(payload)  # type: ignore[arg-type]

    return []


__all__ = ["load_revenue_series"]
