from __future__ import annotations

from typing import Any

from app.ai.datasets import load_revenue_series
from app.ai.utils import iqr_bounds, rolling_z_scores


def _resolve_anomaly_config(payload: Any, threshold: float, method: str, window: int) -> tuple[float, str, int]:
    if isinstance(payload, dict):
        threshold = float(payload.get("threshold", threshold) or threshold)
        method = str(payload.get("method", method) or method).lower()
        window = int(payload.get("window", window) or window)
    if method not in {"zscore", "iqr"}:
        method = "zscore"
    return threshold, method, max(3, window)


def _detect_with_zscores(
    series: list[float], threshold: float, window: int
) -> tuple[list[dict[str, Any]], list[float]]:
    scores = rolling_z_scores(series, window=window)
    anomalies = []
    for idx, (value, score) in enumerate(zip(series, scores, strict=True)):
        if abs(score) < threshold:
            continue
        anomalies.append(
            {
                "index": idx,
                "value": value,
                "z_score": score,
                "method": "zscore",
                "explanation": (
                    "Spike detected" if score > 0 else "Drop detected"
                )
                + f" (z={score:.2f}, threshold={threshold})",
            }
        )
    return anomalies, scores


def _detect_with_iqr(series: list[float], factor: float) -> tuple[list[dict[str, Any]], list[float]]:
    bounds = iqr_bounds(series, factor)
    if not bounds:
        return [], []
    lower, upper = bounds
    anomalies: list[dict[str, Any]] = []
    scores: list[float] = []
    for idx, value in enumerate(series):
        if value < lower or value > upper:
            deviation = (value - upper) if value > upper else (value - lower)
            scores.append(deviation)
            anomalies.append(
                {
                    "index": idx,
                    "value": value,
                    "method": "iqr",
                    "explanation": f"Outlier detected (IQR bounds {lower:.2f}-{upper:.2f})",
                }
            )
        else:
            scores.append(0.0)
    return anomalies, scores


def detect_anomalies(payload: Any, threshold: float = 2.5, method: str = "zscore", window: int = 5) -> dict[str, Any]:
    """
    Identify anomalies in a revenue series using configurable z-score or IQR approaches.
    """
    series = load_revenue_series(payload)
    if not series:
        return {
            "anomalies": [],
            "z_scores": [],
            "threshold": threshold,
            "score": None,
            "method": method,
            "narrative": "No data supplied.",
        }

    threshold, method, window = _resolve_anomaly_config(payload, threshold, method, window)

    if len(series) < 3:
        return {
            "anomalies": [],
            "z_scores": [0.0 for _ in series],
            "threshold": threshold,
            "score": None,
            "method": method,
            "narrative": "Series too short for anomaly detection.",
        }

    if method == "iqr":
        anomalies, scores = _detect_with_iqr(series, threshold)
        overall_score = max((abs(s) for s in scores), default=None)
        return {
            "anomalies": anomalies,
            "z_scores": scores,
            "threshold": threshold,
            "score": overall_score,
            "method": "iqr",
            "narrative": _build_narrative(anomalies, threshold, method="iqr"),
        }

    scores = rolling_z_scores(series, window=window)
    anomalies = [
        {
            "index": idx,
            "value": value,
            "z_score": score,
            "method": "zscore",
            "explanation": ("Spike detected" if score > 0 else "Drop detected")
            + f" (z={score:.2f}, threshold={threshold})",
        }
        for idx, (value, score) in enumerate(zip(series, scores, strict=True))
        if abs(score) >= threshold
    ]

    overall_score = max(abs(s) for s in scores) if scores else None

    return {
        "anomalies": anomalies,
        "z_scores": scores,
        "threshold": threshold,
        "score": overall_score,
        "method": "zscore",
        "narrative": _build_narrative(anomalies, threshold, method="zscore"),
    }


def _build_narrative(anomalies: list[dict[str, Any]], threshold: float, method: str) -> str:
    if not anomalies:
        if method == "iqr":
            return f"No anomalies detected outside IQR bounds (factor {threshold})."
        return f"No anomalies detected above threshold {threshold}."
    first = anomalies[0]
    z_score = first.get("z_score") or 0
    direction = "increase" if z_score > 0 else "decrease"
    return (
        f"{len(anomalies)} anomaly{'ies' if len(anomalies)!=1 else ''} flagged. "
        f"Largest {direction} at index {first['index']} (threshold={threshold})."
    )


run_anomaly_detection = detect_anomalies


__all__ = ["detect_anomalies", "run_anomaly_detection"]
