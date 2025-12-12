import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import Card from "../../components/ui/Card.jsx";
import Button from "../../components/ui/Button.jsx";
import RevenueForecastChart from "../../components/charts/RevenueForecastChart.jsx";

const Forecast = () => {
  return (
    <MainLayout>
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem" }}>
        <RevenueForecastChart />
        <Card title="Run forecast">
          <p style={{ color: "#475569" }}>Placeholder controls for forecasting.</p>
          <Button>Run</Button>
        </Card>
      </div>
    </MainLayout>
  );
};

export default Forecast;
