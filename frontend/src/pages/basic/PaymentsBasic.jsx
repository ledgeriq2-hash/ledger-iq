import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const data = [
  { id: "PMT-01", customer: "Acme", amount: "$300", method: "Card" },
  { id: "PMT-02", customer: "Globex", amount: "$900", method: "Bank" },
];

const PaymentsBasic = () => {
  return (
    <MainLayout>
      <GenericTable
        title="Payments"
        columns={[
          { Header: "ID", accessor: "id" },
          { Header: "Customer", accessor: "customer" },
          { Header: "Amount", accessor: "amount" },
          { Header: "Method", accessor: "method" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default PaymentsBasic;
