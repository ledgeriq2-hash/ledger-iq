import React from "react";

import MainLayout from "../../layouts/MainLayout.jsx";
import RevenueForecastChart from "../../components/charts/RevenueForecastChart.jsx";
import CashflowChart from "../../components/charts/CashflowChart.jsx";
import AnomalyTimelineChart from "../../components/charts/AnomalyTimelineChart.jsx";

const DashboardBasic = () => {
  return (
    <MainLayout>
      <div className="cardGridBasic">
        <RevenueForecastChart />
        <CashflowChart />
        <AnomalyTimelineChart />
      </div>
    </MainLayout>
  );
};

export default DashboardBasic;

