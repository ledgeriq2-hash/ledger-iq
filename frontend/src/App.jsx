import { useCallback, useEffect, useState } from "react";
import mlApi from "./api/mlApi.js";
import ErrorState from "./components/ui/ErrorState.jsx";

export default function App() {
  const [latest, setLatest] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadForecast = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await mlApi.getLatestPrediction("forecast");
      setLatest(response ?? null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadForecast();
  }, [loadForecast]);

  if (loading) {
    return <div style={{ padding: 16 }}>Loading forecast...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: 16 }}>
        <ErrorState compact title="Failed to load forecast" error={error} onRetry={loadForecast} />
      </div>
    );
  }

  const metrics = latest?.metrics || {};
  const isAnomaly = !!metrics.anomaly_is_anomaly;
  const statusColor = isAnomaly ? "var(--color-primary)" : "var(--color-secondary)";
  const statusBg = isAnomaly
    ? "color-mix(in srgb, var(--color-primary) 18%, var(--color-bg))"
    : "color-mix(in srgb, var(--color-secondary) 18%, var(--color-bg))";

  const msg = isAnomaly
    ? `⚠️ Anomaly detected in ${metrics.anomaly_period || "unknown"} (z=${Number(
        metrics.anomaly_z_score
      ).toFixed(2)}, threshold=${metrics.anomaly_threshold ?? "?"})`
    : "✅ No anomaly detected";

  return (
    <div style={{ padding: 16, fontFamily: "var(--font-sans)" }}>
      <h2>Ledger IQ Forecast</h2>

      <div
        style={{
          padding: 12,
          borderRadius: 8,
          marginBottom: 16,
          border: "1px solid",
          borderColor: statusColor,
          background: statusBg,
        }}
      >
        <b>{msg}</b>
      </div>

      <h3>Latest forecast (values)</h3>
      <pre
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          padding: 12,
          borderRadius: 8,
          overflowX: "auto",
        }}
      >
        {JSON.stringify(
          {
            run_id: latest?.run_id,
            model_version: latest?.model_version,
            labels: latest?.series?.labels,
            values: latest?.series?.values,
            metrics: latest?.metrics,
          },
          null,
          2
        )}
      </pre>
    </div>
  );
}
