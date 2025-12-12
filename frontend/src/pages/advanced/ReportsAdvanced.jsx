import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const ReportsAdvanced = () => {
  const data = [
    { type: "Income Statement", status: "Ready" },
    { type: "Cashflow", status: "Queued" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Reports"
        columns={[
          { Header: "Type", accessor: "type" },
          { Header: "Status", accessor: "status" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default ReportsAdvanced;
