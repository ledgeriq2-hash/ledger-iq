import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import RevenueForecastChart from "../../components/charts/RevenueForecastChart.jsx";
import AnomalyTimelineChart from "../../components/charts/AnomalyTimelineChart.jsx";
import Card from "../../components/ui/Card.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";

const AIAdvanced = () => {
  return (
    <MainLayout>
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem" }}>
        <RevenueForecastChart />
        <AnomalyTimelineChart />
      </div>
      <div style={{ marginTop: "1rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
        <Card title="Forecast">
          <div style={{ display: "grid", gap: "0.5rem" }}>
            <div style={{ color: "var(--color-muted)", fontWeight: 700 }}>Last updated: —</div>
            <EmptyState
              compact
              title="AI results will appear here once connected."
              message="Forecast output is disabled in this phase."
            />
          </div>
        </Card>
        <Card title="Anomaly detection">
          <div style={{ display: "grid", gap: "0.5rem" }}>
            <div style={{ color: "var(--color-muted)", fontWeight: 700 }}>Last updated: —</div>
            <EmptyState
              compact
              title="AI results will appear here once connected."
              message="Anomaly detection is disabled in this phase."
            />
          </div>
        </Card>
      </div>
    </MainLayout>
  );
};

export default AIAdvanced;
