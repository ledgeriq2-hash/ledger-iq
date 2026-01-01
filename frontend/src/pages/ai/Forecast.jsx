import React from "react";

import MainLayout from "../../layouts/MainLayout.jsx";
import Card from "../../components/ui/Card.jsx";
import RevenueForecastChart from "../../components/charts/RevenueForecastChart.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import Tag from "../../components/ui/Tag.jsx";

const Forecast = () => {
  return (
    <MainLayout>
      <div className="splitGrid">
        <RevenueForecastChart />
        <Card title="Forecast" subtitle="Display-only placeholder">
          <div className="u-grid u-gap-2">
            <Tag>Advisory Only</Tag>
            <div className="dashboardMeta">Last updated: ?</div>
            <EmptyState compact title="AI results will appear here once connected." message="Forecast output is disabled in this phase." />
          </div>
        </Card>
      </div>
    </MainLayout>
  );
};

export default Forecast;
