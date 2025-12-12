import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const PaymentsAdvanced = () => {
  const data = [
    { id: "PMT-91", customer: "Acme", amount: "$2,400", method: "Wire", applied: "$1,900" },
    { id: "PMT-92", customer: "Globex", amount: "$1,100", method: "Card", applied: "$1,100" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Payments"
        columns={[
          { Header: "ID", accessor: "id" },
          { Header: "Customer", accessor: "customer" },
          { Header: "Amount", accessor: "amount" },
          { Header: "Applied", accessor: "applied" },
          { Header: "Method", accessor: "method" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default PaymentsAdvanced;
