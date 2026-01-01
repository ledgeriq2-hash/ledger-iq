import React, { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import aiApi from "../../api/aiApi.js";
import mlApi from "../../api/mlApi.js";
import AnomalyTimelineChart from "../../components/charts/AnomalyTimelineChart.jsx";
import RevenueForecastChart from "../../components/charts/RevenueForecastChart.jsx";
import Button from "../../components/ui/Button.jsx";
import Card from "../../components/ui/Card.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";
import Input from "../../components/ui/Input.jsx";
import Skeleton from "../../components/ui/Skeleton.jsx";
import Tag from "../../components/ui/Tag.jsx";
import Table from "../../components/kit/Table.jsx";
import { useAiInsights, useAiOverview } from "../../hooks/useAIInsights.js";

const DEFAULT_FILTERS = {
  from_date: "",
  to_date: "",
  severity: "",
  type: "",
  min_confidence: "",
};

const formatDateTime = (value) => {
  if (!value) return "?";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
};

const AIOverview = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [draftFilters, setDraftFilters] = useState(DEFAULT_FILTERS);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  const overviewQuery = useAiOverview();
  const insightsQuery = useAiInsights(filters);
  const forecastQuery = useQuery({
    queryKey: ["ml", "forecast", "latest"],
    queryFn: () => mlApi.getLatestPrediction("forecast"),
    staleTime: 30_000,
  });
  const runsQuery = useQuery({
    queryKey: ["ai", "runs"],
    queryFn: () => aiApi.listRuns(),
    staleTime: 15_000,
  });
  const logsQuery = useQuery({
    queryKey: ["ai", "logs"],
    queryFn: () => aiApi.listLogs(),
    staleTime: 15_000,
  });

  const anomalies = useMemo(() => {
    const insights = insightsQuery.data?.insights || [];
    return insights.filter((item) => String(item.type || "").toLowerCase().includes("anomaly")).slice(0, 6);
  }, [insightsQuery.data]);

  const alertItems = useMemo(() => {
    const backend = Array.isArray(overviewQuery.data?.alerts)
      ? overviewQuery.data.alerts.map((alert) => ({ ...alert, source: "Backend" }))
      : [];
    const derived = Array.isArray(insightsQuery.data?.insights)
      ? insightsQuery.data.insights.slice(0, 4).map((alert) => ({
          id: alert.id,
          title: alert.title || "AI Insight",
          description: alert.message,
          created_at: alert.created_at,
          source: "Derived",
        }))
      : [];
    return [...backend, ...derived].slice(0, 6);
  }, [overviewQuery.data, insightsQuery.data]);

  const lastUpdated = useMemo(() => {
    const candidates = [
      forecastQuery.data?.created_at,
      overviewQuery.data?.alerts?.[0]?.created_at,
      insightsQuery.data?.insights?.[0]?.created_at,
      runsQuery.data?.items?.[0]?.created_at,
    ].filter(Boolean);
    return candidates[0] || null;
  }, [forecastQuery.data, overviewQuery.data, insightsQuery.data, runsQuery.data]);

  const runs = runsQuery.data?.items || [];
  const logs = logsQuery.data?.items || [];

  const retryAlerts = () => {
    queryClient.invalidateQueries({ queryKey: ["ai", "overview"] });
    queryClient.invalidateQueries({ queryKey: ["ai", "insights"] });
  };

  return (
    <div className="u-pad-5 u-grid u-gap-5" data-testid="ai-overview">
      <div>
        <div className="u-flex u-items-center u-gap-2">
          <h1 className="u-m-0">{t("nav.aiOverview", { defaultValue: "AI Overview" })}</h1>
          <Tag>Advisory Only</Tag>
        </div>
        <div className="u-text-muted">Last updated: {lastUpdated ? formatDateTime(lastUpdated) : "?"}</div>
      </div>

      <div className="cardGrid">
        <Card title={t("ai.anomalies", { defaultValue: "Anomalies detected" })}>
          {overviewQuery.isLoading ? (
            <Skeleton className="kit-skeletonLg" />
          ) : overviewQuery.isError ? (
            <ErrorState compact title="Failed to load anomalies" error={overviewQuery.error} onRetry={overviewQuery.refetch} />
          ) : (
            <div className="dashboardKpiValue">{overviewQuery.data?.anomalies_count ?? 0}</div>
          )}
        </Card>
        <Card title={t("ai.forecast", { defaultValue: "Forecast summary" })}>
          {overviewQuery.isLoading ? (
            <Skeleton className="kit-skeletonLg" />
          ) : overviewQuery.isError ? (
            <ErrorState compact title="Failed to load forecast summary" error={overviewQuery.error} onRetry={overviewQuery.refetch} />
          ) : overviewQuery.data?.forecast_summary?.text ? (
            <div className="u-text-muted">{overviewQuery.data.forecast_summary.text}</div>
          ) : (
            <EmptyState compact title="No summary yet" message="Run the AI pipeline to generate a forecast summary." />
          )}
        </Card>
      </div>

      <div className="dashboardChartsGrid">
        {forecastQuery.isLoading ? (
          <Card title="Revenue Forecast">
            <Skeleton className="kit-skeletonChart" />
          </Card>
        ) : forecastQuery.isError ? (
          <Card title="Revenue Forecast">
            <ErrorState compact title="Failed to load forecast" error={forecastQuery.error} onRetry={forecastQuery.refetch} />
          </Card>
        ) : (
          <RevenueForecastChart data={forecastQuery.data} />
        )}

        {insightsQuery.isLoading ? (
          <Card title="Anomaly Timeline">
            <Skeleton className="kit-skeletonChart" />
          </Card>
        ) : insightsQuery.isError ? (
          <Card title="Anomaly Timeline">
            <ErrorState compact title="Failed to load anomalies" error={insightsQuery.error} onRetry={insightsQuery.refetch} />
          </Card>
        ) : (
          <AnomalyTimelineChart data={anomalies} />
        )}
      </div>

      <Card title="Insight filters" subtitle="Filters are applied to anomalies and derived alerts.">
        <div className="wizardStepsGrid">
          <Input
            label="From date"
            type="date"
            value={draftFilters.from_date}
            onChange={(event) => setDraftFilters((prev) => ({ ...prev, from_date: event.target.value }))}
          />
          <Input
            label="To date"
            type="date"
            value={draftFilters.to_date}
            onChange={(event) => setDraftFilters((prev) => ({ ...prev, to_date: event.target.value }))}
          />
          <Input
            label="Severity"
            value={draftFilters.severity}
            onChange={(event) => setDraftFilters((prev) => ({ ...prev, severity: event.target.value }))}
            placeholder="low/medium/high"
          />
          <Input
            label="Type"
            value={draftFilters.type}
            onChange={(event) => setDraftFilters((prev) => ({ ...prev, type: event.target.value }))}
            placeholder="anomaly/forecast"
          />
          <Input
            label="Min confidence"
            inputMode="decimal"
            value={draftFilters.min_confidence}
            onChange={(event) => setDraftFilters((prev) => ({ ...prev, min_confidence: event.target.value }))}
            placeholder="0.7"
          />
        </div>
        <div className="wizardActionsRow">
          <Button
            variant="ghost"
            type="button"
            onClick={() => {
              setDraftFilters(DEFAULT_FILTERS);
              setFilters(DEFAULT_FILTERS);
            }}
          >
            Reset filters
          </Button>
          <Button type="button" onClick={() => setFilters(draftFilters)}>
            Apply filters
          </Button>
        </div>
      </Card>

      <Card title={t("ai.alerts", { defaultValue: "Recent AI alerts" })}>
        {overviewQuery.isLoading || insightsQuery.isLoading ? (
          <Skeleton className="kit-skeletonLg" />
        ) : overviewQuery.isError || insightsQuery.isError ? (
          <ErrorState compact title="Failed to load alerts" error={overviewQuery.error || insightsQuery.error} onRetry={retryAlerts} />
        ) : alertItems.length === 0 ? (
          <EmptyState title="No alerts yet" message="Alerts will appear once the AI service detects changes." />
        ) : (
          <div className="u-grid u-gap-3">
            {alertItems.map((alert) => (
              <div key={alert.id} className="notificationItem">
                <div className="notificationHeader">
                  <div className="notificationTitle">{alert.title}</div>
                  <Tag tone={alert.source === "Backend" ? "success" : "warning"}>{alert.source}</Tag>
                </div>
                <div className="notificationBody">{alert.description}</div>
                <div className="notificationMeta">{formatDateTime(alert.created_at)}</div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <div className="splitGrid">
        <Card title="AI Runs">
          {runsQuery.isLoading ? (
            <Skeleton className="kit-skeletonLg" />
          ) : runsQuery.isError ? (
            <ErrorState compact title="Failed to load runs" error={runsQuery.error} onRetry={runsQuery.refetch} />
          ) : runs.length === 0 ? (
            <EmptyState compact title="No runs yet" message="Trigger a run to see the latest status here." />
          ) : (
            <Table
              keyField="id"
              columns={[
                { key: "status", header: "Status", render: (row) => <Tag>{row.status}</Tag> },
                { key: "started_at", header: "Started", render: (row) => formatDateTime(row.started_at) },
                { key: "finished_at", header: "Finished", render: (row) => (row.finished_at ? formatDateTime(row.finished_at) : "-") },
                { key: "error", header: "Error", render: (row) => row.error || "-" },
              ]}
              rows={runs.slice(0, 6)}
            />
          )}
        </Card>

        <Card title="Model Logs">
          {logsQuery.isLoading ? (
            <Skeleton className="kit-skeletonLg" />
          ) : logsQuery.isError ? (
            <ErrorState compact title="Failed to load logs" error={logsQuery.error} onRetry={logsQuery.refetch} />
          ) : logs.length === 0 ? (
            <EmptyState compact title="No logs yet" message="Logs appear after model evaluations." />
          ) : (
            <Table
              keyField="id"
              columns={[
                { key: "model_type", header: "Model" },
                { key: "score", header: "Score", render: (row) => row.score || "-" },
                { key: "created_at", header: "Created", render: (row) => formatDateTime(row.created_at) },
              ]}
              rows={logs.slice(0, 6)}
            />
          )}
        </Card>
      </div>
    </div>
  );
};

export default AIOverview;
