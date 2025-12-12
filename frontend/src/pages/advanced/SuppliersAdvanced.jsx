import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const SuppliersAdvanced = () => {
  const data = [
    { name: "Office Supply Co", contact: "supply@example.com", balance: "$210" },
    { name: "Travel Inc", contact: "travel@example.com", balance: "$0" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Suppliers"
        columns={[
          { Header: "Name", accessor: "name" },
          { Header: "Contact", accessor: "contact" },
          { Header: "Balance", accessor: "balance" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default SuppliersAdvanced;
