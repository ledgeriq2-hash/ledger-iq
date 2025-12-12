import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const CustomerInvoices = () => {
  const data = [
    { number: "INV-201", status: "Paid", total: "$420" },
    { number: "INV-202", status: "Sent", total: "$180" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Invoices"
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

export default CustomerInvoices;
