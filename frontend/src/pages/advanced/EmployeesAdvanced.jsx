import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const EmployeesAdvanced = () => {
  const data = [
    { name: "Alex Doe", role: "Accountant", status: "Active" },
    { name: "Jamie Roe", role: "Controller", status: "Active" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Employees"
        columns={[
          { Header: "Name", accessor: "name" },
          { Header: "Role", accessor: "role" },
          { Header: "Status", accessor: "status" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default EmployeesAdvanced;
