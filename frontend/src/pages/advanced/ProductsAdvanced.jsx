import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const ProductsAdvanced = () => {
  const data = [
    { name: "Starter Plan", sku: "SKU-01", price: "$49", stock: "N/A" },
    { name: "Pro Plan", sku: "SKU-02", price: "$99", stock: "N/A" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Products"
        columns={[
          { Header: "Name", accessor: "name" },
          { Header: "SKU", accessor: "sku" },
          { Header: "Price", accessor: "price" },
          { Header: "Stock", accessor: "stock" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default ProductsAdvanced;
