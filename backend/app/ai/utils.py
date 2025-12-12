from __future__ import annotations

from collections.abc import Iterable
from math import sqrt
from statistics import mean, pstdev
from typing import Sequence


def moving_average(data: Sequence[float], window: int) -> list[float]:
    if window <= 0:
        raise ValueError("window must be positive")
    result: list[float] = []
    for i in range(len(data)):
        start = max(0, i - window + 1)
        window_slice = data[start : i + 1]
        result.append(mean(window_slice))
    return result


def z_scores(data: Sequence[float]) -> list[float]:
    if not data:
        return []
    mu = mean(data)
    sigma = pstdev(data)
    if sigma == 0:
        return [0.0 for _ in data]
    return [(x - mu) / sigma for x in data]


def to_float_series(values: Iterable[float | int | str]) -> list[float]:
    series: list[float] = []
    for v in values:
        try:
            series.append(float(v))
        except (TypeError, ValueError):
            continue
    return series


def exponential_smoothing(series: Sequence[float], alpha: float) -> list[float]:
    if not series:
        return []
    alpha = max(0.01, min(alpha, 1.0))
    smoothed: list[float] = [series[0]]
    for value in series[1:]:
        smoothed.append(alpha * value + (1 - alpha) * smoothed[-1])
    return smoothed


def rmse(actual: Sequence[float], predicted: Sequence[float]) -> float | None:
    if not actual or not predicted or len(actual) != len(predicted):
        return None
    return sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual))


def mape(actual: Sequence[float], predicted: Sequence[float]) -> float | None:
    if not actual or not predicted or len(actual) != len(predicted):
        return None
    errors = []
    for a, p in zip(actual, predicted):
        if a == 0:
            continue
        errors.append(abs((a - p) / a))
    if not errors:
        return None
    return sum(errors) / len(errors)


def rolling_z_scores(series: Sequence[float], window: int, eps: float = 1e-8) -> list[float]:
    """Compute rolling z-scores to better adapt to local level shifts."""
    if not series:
        return []
    window = max(2, window)
    scores: list[float] = []
    for idx, value in enumerate(series):
        start = max(0, idx - window + 1)
        window_slice = series[start : idx + 1]
        mu = mean(window_slice)
        sigma = pstdev(window_slice) or eps
        scores.append((value - mu) / sigma)
    return scores


def iqr_bounds(series: Sequence[float], factor: float = 1.5) -> tuple[float, float] | None:
    if not series:
        return None
    sorted_series = sorted(series)
    n = len(sorted_series)
    q1_idx = n // 4
    q3_idx = (3 * n) // 4
    q1 = sorted_series[q1_idx]
    q3 = sorted_series[q3_idx]
    iqr = q3 - q1
    lower = q1 - factor * iqr
    upper = q3 + factor * iqr
    return lower, upper


__all__ = [
    "moving_average",
    "z_scores",
    "to_float_series",
    "exponential_smoothing",
    "rmse",
    "mape",
    "rolling_z_scores",
    "iqr_bounds",
]
