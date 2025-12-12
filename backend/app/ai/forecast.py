from __future__ import annotations

from typing import Any

from app.ai.datasets import load_revenue_series
from app.ai.utils import exponential_smoothing, mape, rmse


def _resolve_config(payload: Any, window: int, horizon: int, alpha: float) -> tuple[int, int, float]:
    if isinstance(payload, dict):
        window = int(payload.get("window", window) or window)
        horizon = int(payload.get("horizon", payload.get("horizon_days", horizon)) or horizon)
        alpha = float(payload.get("alpha", payload.get("smoothing_factor", alpha)) or alpha)
    return max(1, window), max(0, horizon), max(0.01, min(alpha, 1.0))


def generate_forecast(payload: Any, window: int = 3, horizon: int = 3, alpha: float = 0.5) -> dict[str, Any]:
    """
    Exponential smoothing forecast with configurable window/horizon.

    Returns forecasted values, baseline, confidence, intervals, and error metrics (MAPE, RMSE).
    """
    series = load_revenue_series(payload)
    if not series:
        return {
            "forecast": [],
            "baseline": [],
            "confidence": None,
            "intervals": {"lower": [], "upper": []},
            "mape": None,
            "rmse": None,
        }

    window, horizon, alpha = _resolve_config(payload, window, horizon, alpha)
    series_window = series[-window:] if window > 0 else series
    smoothed = exponential_smoothing(series_window, alpha)
    last_level = smoothed[-1]
    forecast_values = [last_level for _ in range(horizon)]

    residuals = [actual - fitted for actual, fitted in zip(series_window, smoothed)]
    residual_std = (sum((r ** 2 for r in residuals)) / len(residuals)) ** 0.5 if residuals else 0
    spread = residual_std or (abs(last_level) * 0.1)
    lower = [max(0, v - spread) for v in forecast_values]
    upper = [v + spread for v in forecast_values]

    rmse_value = rmse(series_window[-len(smoothed) :], smoothed)
    mape_value = mape(series_window[-len(smoothed) :], smoothed)

    return {
        "baseline": series,
        "forecast": forecast_values,
        "confidence": 0.65,
        "intervals": {"lower": lower, "upper": upper},
        "mape": mape_value,
        "rmse": rmse_value,
    }


run_forecast = generate_forecast


__all__ = ["generate_forecast", "run_forecast"]
