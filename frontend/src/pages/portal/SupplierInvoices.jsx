import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const SupplierInvoices = () => {
  const data = [
    { number: "BILL-301", status: "Open", total: "$410" },
    { number: "BILL-302", status: "Paid", total: "$210" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Bills"
        columns={[
          { Header: "Number", accessor: "number" },
          { Header: "Status", accessor: "status" },
          { Header: "Total", accessor: "total" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default SupplierInvoices;
