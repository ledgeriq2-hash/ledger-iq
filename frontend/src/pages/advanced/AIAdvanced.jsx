import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import RevenueForecastChart from "../../components/charts/RevenueForecastChart.jsx";
import AnomalyTimelineChart from "../../components/charts/AnomalyTimelineChart.jsx";
import Card from "../../components/ui/Card.jsx";
import Button from "../../components/ui/Button.jsx";

const AIAdvanced = () => {
  return (
    <MainLayout>
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem" }}>
        <RevenueForecastChart />
        <AnomalyTimelineChart />
      </div>
      <div style={{ marginTop: "1rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
        <Card title="Forecast">
          <p style={{ color: "#475569" }}>Generate quick forecasts based on recent revenue series.</p>
          <Button>Run forecast</Button>
        </Card>
        <Card title="Anomaly detection">
          <p style={{ color: "#475569" }}>Scan for outliers across revenue timeline.</p>
          <Button>Detect anomalies</Button>
        </Card>
      </div>
    </MainLayout>
  );
};

export default AIAdvanced;
