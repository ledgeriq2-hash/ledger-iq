import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const data = [
  { id: "EXP-01", supplier: "Office Supply Co", amount: "$120", category: "Office" },
  { id: "EXP-02", supplier: "Travel Inc", amount: "$650", category: "Travel" },
];

const ExpensesBasic = () => {
  return (
    <MainLayout>
      <GenericTable
        title="Expenses"
        columns={[
          { Header: "ID", accessor: "id" },
          { Header: "Supplier", accessor: "supplier" },
          { Header: "Amount", accessor: "amount" },
          { Header: "Category", accessor: "category" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default ExpensesBasic;
