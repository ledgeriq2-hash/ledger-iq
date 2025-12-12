import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const BalanceSheet = () => {
  const data = [
    { line: "Assets", amount: "$50,000" },
    { line: "Liabilities", amount: "$20,000" },
    { line: "Equity", amount: "$30,000" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Balance Sheet"
        columns={[
          { Header: "Line", accessor: "line" },
          { Header: "Amount", accessor: "amount" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default BalanceSheet;
