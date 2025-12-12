import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const JournalEntries = () => {
  const data = [
    { date: "2024-05-01", description: "Revenue", reference: "JE-1001" },
    { date: "2024-05-02", description: "Expense", reference: "JE-1002" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Journal Entries"
        columns={[
          { Header: "Date", accessor: "date" },
          { Header: "Description", accessor: "description" },
          { Header: "Reference", accessor: "reference" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default JournalEntries;
