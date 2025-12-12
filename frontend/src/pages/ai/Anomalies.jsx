import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import Card from "../../components/ui/Card.jsx";
import Button from "../../components/ui/Button.jsx";
import AnomalyTimelineChart from "../../components/charts/AnomalyTimelineChart.jsx";

const Anomalies = () => {
  return (
    <MainLayout>
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem" }}>
        <AnomalyTimelineChart />
        <Card title="Run anomaly detection">
          <p style={{ color: "#475569" }}>Placeholder controls for anomaly detection.</p>
          <Button>Detect</Button>
        </Card>
      </div>
    </MainLayout>
  );
};

export default Anomalies;
