import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";
import CustomerForm from "../../components/forms/CustomerForm.jsx";
import Card from "../../components/ui/Card.jsx";

const CustomersAdvanced = () => {
  const data = [
    { name: "Acme", tier: "Enterprise", ar: "$12,000" },
    { name: "Globex", tier: "Growth", ar: "$6,500" },
  ];
  return (
    <MainLayout>
      <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "2fr 1fr" }}>
        <GenericTable
          title="Customers"
          columns={[
            { Header: "Name", accessor: "name" },
            { Header: "Tier", accessor: "tier" },
            { Header: "A/R", accessor: "ar" },
          ]}
          data={data}
        />
        <Card title="Add customer">
          <CustomerForm onSubmit={(v) => console.log(v)} />
        </Card>
      </div>
    </MainLayout>
  );
};

export default CustomersAdvanced;
