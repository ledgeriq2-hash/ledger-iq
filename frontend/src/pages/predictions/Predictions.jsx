import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Button from "../../components/ui/Button.jsx";
import Card from "../../components/ui/Card.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";
import Modal from "../../components/ui/Modal.jsx";
import Skeleton from "../../components/ui/Skeleton.jsx";
import Tag from "../../components/ui/Tag.jsx";
import TimeSeriesChart from "../../components/charts/TimeSeriesChart.jsx";
import { api } from "../../api/generated/index.js";
import { useDashboardMetrics } from "../../hooks/useDashboardMetrics.js";
import { useLatestPrediction } from "../../hooks/useLatestPrediction.js";

const money = (value, currency = "USD") => {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(Number(value || 0));
  } catch {
    return String(value ?? 0);
  }
};

const nextMonthKey = (ym) => {
  const m = /^(\d{4})-(\d{2})$/.exec(String(ym || ""));
  if (!m) return null;
  let year = Number(m[1]);
  let month = Number(m[2]);
  month += 1;
  if (month === 13) {
    month = 1;
    year += 1;
  }
  return `${year.toString().padStart(4, "0")}-${month.toString().padStart(2, "0")}`;
};

const Predictions = () => {
  const latestPredictionType = "forecast";
  const [howToOpen, setHowToOpen] = useState(false);

  const metricsQuery = useDashboardMetrics({ months: 12 });

  const latestPredictionQuery = useLatestPrediction(latestPredictionType, null, {
    staleTime: 30_000,
    retry: false,
  });

  const baselinePoints = useMemo(() => {
    const series = metricsQuery.data?.charts?.revenue_by_month || [];
    if (!Array.isArray(series)) return [];
    return series.map((p) => ({ month: p.month, revenue: Number(p.revenue || 0) }));
  }, [metricsQuery.data]);

  const revenueValues = useMemo(() => baselinePoints.map((p) => p.revenue), [baselinePoints]);

  const forecastQuery = useQuery({
    queryKey: ["ai", "forecast", { baseline: revenueValues.slice(-12), horizon: 6 }],
    enabled: !metricsQuery.isLoading && !metricsQuery.isError && revenueValues.length >= 3,
    queryFn: async () => {
      const payload = {
        horizon_days: 6,
        data: revenueValues.slice(-12),
        window: Math.min(6, revenueValues.length),
        alpha: 0.5,
      };
      const res = await api.ai.forecast(payload);
      return res;
    },
    staleTime: 0,
  });

  const refreshLatestPrediction = latestPredictionQuery.refetch;
  const refreshMetrics = metricsQuery.refetch;
  const refreshForecast = forecastQuery.refetch;

  const meta = forecastQuery.data || null;
  const currency = metricsQuery.data?.currency || "USD";

  const futureLabels = useMemo(() => {
    const last = baselinePoints?.[baselinePoints.length - 1]?.month;
    const out = [];
    let cur = last;
    const horizon = meta?.forecast?.length || 0;
    for (let i = 0; i < horizon; i += 1) {
      cur = nextMonthKey(cur) || cur;
      out.push(cur || `+${i + 1}`);
    }
    return out;
  }, [baselinePoints, meta?.forecast?.length]);

  const forecastPoints = useMemo(() => {
    const values = meta?.forecast || [];
    if (!Array.isArray(values) || values.length === 0) return [];
    return values.map((v, i) => ({ x: futureLabels[i], y: Number(v || 0) }));
  }, [meta?.forecast, futureLabels]);

  const intervalPoints = useMemo(() => {
    const lower = meta?.intervals?.lower || meta?.intervals?.low || null;
    const upper = meta?.intervals?.upper || meta?.intervals?.high || null;
    if (!Array.isArray(lower) || !Array.isArray(upper) || lower.length !== upper.length || lower.length !== forecastPoints.length) return [];
    return futureLabels.map((label, i) => ({ x: label, y_low: Number(lower[i] || 0), y_high: Number(upper[i] || 0) }));
  }, [meta?.intervals, forecastPoints.length, futureLabels]);

  const latestPrediction = latestPredictionQuery.data || null;
  const mlSeries = latestPrediction?.series || {};

  const mlForecastPoints = useMemo(() => {
    if (!latestPrediction) return [];

    if (Array.isArray(mlSeries.points)) {
      return mlSeries.points.map((p) => ({
        x: p?.x ?? p?.label ?? p?.month ?? p?.period ?? "",
        y: p?.y ?? p?.value ?? p?.revenue ?? 0,
      }));
    }

    if (Array.isArray(mlSeries.labels) && Array.isArray(mlSeries.values) && mlSeries.labels.length === mlSeries.values.length) {
      return mlSeries.labels.map((label, i) => ({ x: label, y: mlSeries.values[i] }));
    }

    if (Array.isArray(mlSeries.periods) && Array.isArray(mlSeries.forecast) && mlSeries.periods.length === mlSeries.forecast.length) {
      return mlSeries.periods.map((label, i) => ({ x: label, y: mlSeries.forecast[i] }));
    }

    return [];
  }, [latestPrediction, mlSeries]);

  const mlIntervalPoints = useMemo(() => {
    if (!latestPrediction) return [];

    const intervals = mlSeries.intervals || null;
    const labels = mlSeries.labels || mlSeries.periods || null;
    const lower = intervals?.lower || intervals?.low || mlSeries.lower || mlSeries.low || null;
    const upper = intervals?.upper || intervals?.high || mlSeries.upper || mlSeries.high || null;
    if (!Array.isArray(labels) || !Array.isArray(lower) || !Array.isArray(upper)) return [];
    if (labels.length !== lower.length || labels.length !== upper.length) return [];
    return labels.map((label, i) => ({ x: label, y_low: lower[i], y_high: upper[i] }));
  }, [latestPrediction, mlSeries]);

  const formatDateTime = (value) => {
    if (!value) return "—";
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return String(value);
    return dt.toLocaleString();
  };

  return (
    <div className="u-grid u-gap-4" data-testid="predictions">
      <div className="u-grid u-gap-1" data-testid="ai-overview">
        <div className="u-flex u-items-center u-gap-2">
          <h1 className="u-m-0">Predictions</h1>
          <Tag>Advisory Only</Tag>
        </div>
        <div className="u-text-muted">Forecasted revenue with confidence bands.</div>
      </div>

      <Card title="ML forecast" subtitle="Latest prediction output">
        {latestPredictionQuery.isLoading ? (
          <Skeleton className="kit-skeletonChart" />
        ) : latestPredictionQuery.isError ? (
          <ErrorState title="Couldn't load ML forecast" error={latestPredictionQuery.error} onRetry={() => refreshLatestPrediction()} />
        ) : !latestPrediction ? (
          <EmptyState
            title="No ML predictions yet"
            message="Ingest a prediction to see the latest ML forecast."
            action={
              <div className="u-mt-2">
                <Button onClick={() => setHowToOpen(true)}>How to ingest</Button>
              </div>
            }
          />
        ) : mlForecastPoints.length ? (
          <TimeSeriesChart
            actual={metricsQuery.isSuccess ? baselinePoints : []}
            forecast={mlForecastPoints}
            intervals={mlIntervalPoints}
            height={240}
            yFormatter={(v) => money(v, currency)}
          />
        ) : (
          <div className="u-grid u-gap-2">
            <EmptyState compact title="Series format not chartable" message="Showing raw series payload." />
            <pre className="mono">{JSON.stringify(latestPrediction.series, null, 2)}</pre>
          </div>
        )}
      </Card>

      <div className="cardGrid">
        <Card title="Model metadata" subtitle="Run details">
          {latestPredictionQuery.isLoading ? (
            <Skeleton className="kit-skeletonLg" />
          ) : latestPredictionQuery.isError ? (
            <ErrorState compact title="Couldn't load model metadata" error={latestPredictionQuery.error} onRetry={() => refreshLatestPrediction()} />
          ) : latestPrediction ? (
            <div className="u-grid u-gap-2">
              <div className="kvRow">
                <div className="kvKey">Prediction type</div>
                <div className="kvValue">{latestPrediction.prediction_type || "—"}</div>
              </div>
              <div className="kvRow">
                <div className="kvKey">Model version</div>
                <div className="kvValue">{latestPrediction.model_version || "—"}</div>
              </div>
              <div className="kvRow">
                <div className="kvKey">Run ID</div>
                <div className="kvValue mono">{latestPrediction.run_id || "—"}</div>
              </div>
              <div className="kvRow">
                <div className="kvKey">Data snapshot ID</div>
                <div className="kvValue mono">{latestPrediction.data_snapshot_id || "—"}</div>
              </div>
              <div className="kvRow">
                <div className="kvKey">Created at</div>
                <div className="kvValue">{formatDateTime(latestPrediction.created_at)}</div>
              </div>
            </div>
          ) : (
            <EmptyState compact title="No ML prediction yet" message="Ingest a prediction to view ML run details." />
          )}
        </Card>

        <Card title="Quality" subtitle="Baseline fit">
          {latestPredictionQuery.isLoading ? (
            <Skeleton className="kit-skeletonLg" />
          ) : latestPredictionQuery.isError ? (
            <ErrorState compact title="Couldn't load model metrics" error={latestPredictionQuery.error} onRetry={() => refreshLatestPrediction()} />
          ) : latestPrediction ? (
            <div className="u-grid u-gap-2">
              <div className="kvRow">
                <div className="kvKey">MAPE</div>
                <div className="kvValue">{latestPrediction.metrics?.mape ?? "—"}</div>
              </div>
              <div className="kvRow">
                <div className="kvKey">RMSE</div>
                <div className="kvValue">{latestPrediction.metrics?.rmse ?? "—"}</div>
              </div>
            </div>
          ) : (
            <EmptyState compact title="No ML metrics" message="Ingest a prediction to view ML metrics." />
          )}
        </Card>
      </div>

      <Card title="Heuristic forecast (demo)" subtitle="Optional fallback (not ML)">
        {metricsQuery.isLoading || (forecastQuery.isLoading && forecastQuery.isFetching) ? (
          <Skeleton className="kit-skeletonChart" />
        ) : metricsQuery.isError ? (
          <ErrorState
            title="Couldn't load baseline data"
            message="Dashboard metrics are required to generate the demo forecast."
            error={metricsQuery.error}
            onRetry={() => refreshMetrics()}
          />
        ) : baselinePoints.length < 3 ? (
          <EmptyState title="Not enough data" message="Add more revenue history to generate a demo forecast." />
        ) : forecastQuery.isError ? (
          <ErrorState title="Forecast failed" error={forecastQuery.error} onRetry={() => refreshForecast()} />
        ) : (
          <TimeSeriesChart
            actual={baselinePoints}
            forecast={forecastPoints}
            intervals={intervalPoints}
            height={240}
            yFormatter={(v) => money(v, currency)}
          />
        )}
      </Card>

      <Modal
        open={howToOpen}
        title="How to ingest"
        onClose={() => setHowToOpen(false)}
        actions={
          <Button variant="secondary" onClick={() => setHowToOpen(false)}>
            Got it
          </Button>
        }
      >
        <div className="u-grid u-gap-2">
          <div className="u-text-muted">POST a prediction to the backend ingest endpoint, then refresh this page.</div>
          <pre className="mono">{`POST /api/v1/ml/predictions/ingest\n\n{\n  \"prediction_type\": \"forecast\",\n  \"horizon\": 6,\n  \"granularity\": \"month\",\n  \"from_date\": \"2025-01-01\",\n  \"to_date\": \"2025-12-01\",\n  \"series\": { \"points\": [{\"x\":\"2026-01\",\"y\":1234}] },\n  \"model_version\": \"my-model-v1\",\n  \"data_snapshot_id\": \"00000000-0000-0000-0000-000000000000\",\n  \"metrics\": {},\n  \"params\": {}\n}`}</pre>
          <div className="u-text-muted">API docs: `/docs`</div>
        </div>
      </Modal>
    </div>
  );
};

export default Predictions;
