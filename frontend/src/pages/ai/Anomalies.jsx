import React from "react";

import MainLayout from "../../layouts/MainLayout.jsx";
import Card from "../../components/ui/Card.jsx";
import AnomalyTimelineChart from "../../components/charts/AnomalyTimelineChart.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import Tag from "../../components/ui/Tag.jsx";

const Anomalies = () => {
  return (
    <MainLayout>
      <div className="splitGrid">
        <AnomalyTimelineChart />
        <Card title="Anomaly detection" subtitle="Display-only placeholder">
          <div className="u-grid u-gap-2">
            <Tag>Advisory Only</Tag>
            <div className="dashboardMeta">Last updated: ?</div>
            <EmptyState compact title="AI results will appear here once connected." message="Anomaly detection is disabled in this phase." />
          </div>
        </Card>
      </div>
    </MainLayout>
  );
};

export default Anomalies;
