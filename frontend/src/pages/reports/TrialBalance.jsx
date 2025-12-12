import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import GenericTable from "../../components/tables/GenericTable.jsx";

const TrialBalance = () => {
  const data = [
    { account: "Cash", debit: "$5,000", credit: "$0" },
    { account: "Revenue", debit: "$0", credit: "$10,000" },
  ];
  return (
    <MainLayout>
      <GenericTable
        title="Trial Balance"
        columns={[
          { Header: "Account", accessor: "account" },
          { Header: "Debit", accessor: "debit" },
          { Header: "Credit", accessor: "credit" },
        ]}
        data={data}
      />
    </MainLayout>
  );
};

export default TrialBalance;
