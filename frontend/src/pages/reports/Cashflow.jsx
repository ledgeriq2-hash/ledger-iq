import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const Cashflow = () => {
  const data = [
    { line: "Operating", amount: "$12,000" },
    { line: "Investing", amount: "-$2,000" },
    { line: "Financing", amount: "$1,500" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Cashflow"
        columns={[
          { Header: "Line", accessor: "line" },
          { Header: "Amount", accessor: "amount" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default Cashflow;
