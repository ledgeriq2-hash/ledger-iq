import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const IncomeStatement = () => {
  const data = [
    { line: "Revenue", amount: "$10,000" },
    { line: "COGS", amount: "$4,000" },
    { line: "Gross Profit", amount: "$6,000" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Income Statement"
        columns={[
          { Header: "Line", accessor: "line" },
          { Header: "Amount", accessor: "amount" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default IncomeStatement;
