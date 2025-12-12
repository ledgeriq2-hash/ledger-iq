import React from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import api from "../../utils/api";
import LoadingSpinner from "../../components/common/LoadingSpinner.jsx";
import Card from "../../components/ui/Card.jsx";
import ErrorBox from "../../components/ui/ErrorBox.jsx";
import Banner from "../../components/ui/Banner.jsx";
import colors from "../../design/colors.js";
import spacing from "../../design/spacing.js";

const AIOverview = () => {
  const { t } = useTranslation();
  const { data, isLoading, error } = useQuery({
    queryKey: ["ai", "overview"],
    queryFn: async () => {
      const res = await api.get("/api/v1/ai/overview");
      return res.data;
    },
    retry: 2,
  });

  if (isLoading) {
    return <LoadingSpinner message={t("status.loading", { defaultValue: "Loading AI insights..." })} />;
  }

  if (error) {
    return <ErrorBox message={error?.message || "Failed to load AI insights."} />;
  }

  const anomalies = data?.anomalies_count ?? 0;
  const forecast = data?.forecast_summary ?? {};
  const alerts = data?.alerts ?? [];

  return (
    <div style={{ padding: spacing.lg, display: "grid", gap: spacing.lg }} data-testid="ai-overview">
      <h1 style={{ margin: 0, color: colors.text }}>{t("nav.aiOverview", { defaultValue: "AI Overview" })}</h1>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: spacing.lg }}>
        <Card title={t("ai.anomalies", { defaultValue: "Anomalies detected" })}>
          <div style={{ fontSize: "2rem", fontWeight: 700 }}>{anomalies}</div>
        </Card>
        <Card title={t("ai.forecast", { defaultValue: "Forecast" })}>
          <p style={{ margin: 0, color: colors.textMuted }}>
            {forecast.text || t("ai.forecastPlaceholder", { defaultValue: "Forecast summary coming soon." })}
          </p>
        </Card>
      </div>

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ marginTop: 0, color: colors.text }}>{t("ai.alerts", { defaultValue: "Recent AI alerts" })}</h3>
          <span style={{ color: colors.textMuted }}>
            {alerts.length} {t("ai.items", { defaultValue: "items" })}
          </span>
        </div>
        <div style={{ display: "grid", gap: spacing.md }}>
          {alerts.length === 0 && (
            <Banner message={t("ai.noAlerts", { defaultValue: "No alerts to show." })} variant="info" />
          )}
          {alerts.map((alert) => (
            <div
              key={alert.id}
              style={{
                padding: spacing.md,
                border: `1px solid ${colors.border}`,
                borderRadius: "10px",
                background: colors.surfaceMuted,
              }}
            >
              <div style={{ fontWeight: 600 }}>{alert.title}</div>
              <div style={{ color: colors.textMuted, marginTop: spacing.xs }}>{alert.description}</div>
              <div style={{ color: "#94a3b8", marginTop: spacing.xs, fontSize: "0.9rem" }}>
                {alert.created_at ? new Date(alert.created_at).toLocaleString() : ""}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default AIOverview;
