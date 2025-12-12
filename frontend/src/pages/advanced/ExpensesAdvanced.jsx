import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const ExpensesAdvanced = () => {
  const data = [
    { id: "EXP-201", supplier: "Travel Inc", amount: "$1,200", category: "Travel", project: "Q2" },
    { id: "EXP-202", supplier: "Office Supply Co", amount: "$320", category: "Office", project: "Ops" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Expenses"
        columns={[
          { Header: "ID", accessor: "id" },
          { Header: "Supplier", accessor: "supplier" },
          { Header: "Category", accessor: "category" },
          { Header: "Project", accessor: "project" },
          { Header: "Amount", accessor: "amount" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default ExpensesAdvanced;
