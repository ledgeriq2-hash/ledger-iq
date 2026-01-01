from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.ai.utils import to_float_series
from app.schemas.ai import AiDatasetV1
from pydantic import ValidationError


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
        dataset_value = payload.get("dataset")
        if dataset_value is not None:
            if isinstance(dataset_value, AiDatasetV1):
                return [float(point.value) for point in dataset_value.points]
            if isinstance(dataset_value, dict):
                try:
                    parsed = AiDatasetV1.model_validate(dataset_value)
                    return [float(point.value) for point in parsed.points]
                except ValidationError:
                    pass

    if isinstance(payload, AiDatasetV1):
        return [float(point.value) for point in payload.points]

    if isinstance(payload, dict):
        if "revenues" in payload:
            return to_float_series(payload["revenues"])
        if "data" in payload and isinstance(payload["data"], Iterable):
            values: list[float | int | str] = []
            for item in payload["data"]:
                if isinstance(item, dict) and "value" in item:
                    values.append(item["value"])
                elif not isinstance(item, dict):
                    values.append(item)
            return to_float_series(values)
    if isinstance(payload, Iterable):
        return to_float_series(payload)  # type: ignore[arg-type]

    return []


__all__ = ["load_revenue_series"]
