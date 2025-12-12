from __future__ import annotations

from app.ai import anomaly, forecast


def test_forecast_basic_series():
    payload = {"revenues": [100, 120, 130]}
    result = forecast.generate_forecast(payload, window=2, horizon=2)

    assert result["baseline"] == [100.0, 120.0, 130.0]
    assert len(result["forecast"]) == 2
    assert result["forecast"][0] == result["forecast"][1]  # stable horizon
    assert result["intervals"]["lower"][0] <= result["forecast"][0]
    assert result["intervals"]["upper"][0] >= result["forecast"][0]
    assert result["mape"] is None or result["mape"] >= 0
    assert result["rmse"] is None or result["rmse"] >= 0


def test_forecast_empty_series_safe():
    result = forecast.generate_forecast([], window=3, horizon=3)
    assert result["forecast"] == []
    assert result["baseline"] == []
    assert result["mape"] is None
    assert result["rmse"] is None


def test_forecast_horizon_config_from_payload():
    payload = {"revenues": [10, 12, 14], "horizon": 4, "alpha": 0.8}
    result = forecast.generate_forecast(payload, window=2, horizon=1)
    assert len(result["forecast"]) == 4
    assert result["confidence"] is not None


def test_anomaly_empty_input():
    result = anomaly.detect_anomalies([])
    assert result["anomalies"] == []
    assert result["z_scores"] == []
    assert result["score"] is None


def test_anomaly_simple_spike_detected_zscore():
    series = [10, 10, 10, 50]
    result = anomaly.detect_anomalies({"data": series, "threshold": 2.0, "method": "zscore", "window": 3})
    anomalies = result["anomalies"]
    assert len(anomalies) == 1
    spike = anomalies[0]
    assert spike["index"] == 3
    assert spike["value"] == 50
    assert "Spike" in spike["explanation"]
    assert result["method"] == "zscore"


def test_anomaly_iqr_detects_outlier():
    series = [0, 0, 0, 0, 100]
    result = anomaly.detect_anomalies({"data": series, "method": "iqr", "threshold": 1.5})
    assert len(result["anomalies"]) == 1
    assert result["anomalies"][0]["index"] == 4
    assert result["method"] == "iqr"


def test_anomaly_short_series_safe():
    series = [5]
    result = anomaly.detect_anomalies(series)
    assert result["anomalies"] == []
    assert result["narrative"]


def test_anomaly_many_zeros_no_false_positive():
    series = [0, 0, 0, 0, 0]
    result = anomaly.detect_anomalies(series, threshold=1.0)
    assert result["anomalies"] == []


def test_anomaly_unknown_method_falls_back():
    series = [1, 2, 100]
    result = anomaly.detect_anomalies({"data": series, "method": "unknown", "threshold": 1.0})
    assert result["method"] == "zscore"
