import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import RevenueForecastChart from "../../components/charts/RevenueForecastChart.jsx";
import CashflowChart from "../../components/charts/CashflowChart.jsx";
import AnomalyTimelineChart from "../../components/charts/AnomalyTimelineChart.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const DashboardAdvanced = () => {
  const topCustomers = [
    { name: "Acme Corp", mrr: "$3,200" },
    { name: "Globex", mrr: "$2,150" },
  ];

  return (
    <MainLayout>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem" }}>
        <RevenueForecastChart />
        <CashflowChart />
        <AnomalyTimelineChart />
      </div>
      <div style={{ marginTop: "1rem" }}>
        <GenericTable
          title="Top customers"
          columns={[
            { Header: "Name", accessor: "name" },
            { Header: "MRR", accessor: "mrr" },
          ]}
          data={topCustomers}
        />
      </div>
    </MainLayout>
  );
};

export default DashboardAdvanced;
