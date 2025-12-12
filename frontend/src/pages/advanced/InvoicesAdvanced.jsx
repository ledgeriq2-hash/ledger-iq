import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";
import InvoiceForm from "../../components/forms/InvoiceForm.jsx";
import Card from "../../components/ui/Card.jsx";

const InvoicesAdvanced = () => {
  const data = [
    { number: "INV-301", customer: "Acme", status: "Sent", total: "$5,200" },
    { number: "INV-302", customer: "Globex", status: "Paid", total: "$1,900" },
  ];
  return (
    <MainLayout>
      <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "2fr 1fr" }}>
        <GenericTable
          title="Invoices"
          columns={[
            { Header: "Number", accessor: "number" },
            { Header: "Customer", accessor: "customer" },
            { Header: "Status", accessor: "status" },
            { Header: "Total", accessor: "total" },
          ]}
          data={data}
        />
        <Card title="Create invoice">
          <InvoiceForm onSubmit={(v) => console.log(v)} />
        </Card>
      </div>
    </MainLayout>
  );
};

export default InvoicesAdvanced;
