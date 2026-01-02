import React from "react";
import { Link } from "react-router-dom";

import { useClients } from "../../hooks/useClients.js";
import Button from "../../components/kit/Button.jsx";
import Card from "../../components/kit/Card.jsx";
import Skeleton from "../../components/kit/Skeleton.jsx";
import StatusPill from "../../components/kit/StatusPill.jsx";
import Table from "../../components/kit/Table.jsx";

const money = (value) => {
  if (value === null || value === undefined) return "0.00";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toFixed(2);
};

const balanceTone = (balance) => {
  const n = Number(balance);
  if (Number.isNaN(n) || n === 0) return "info";
  return n > 0 ? "danger" : "success";
};

const Clients = () => {
  const { data, isLoading, error } = useClients({ page: 1, pageSize: 200 });
  const clients = data?.items || [];

  const columns = [
    {
      key: "name",
      header: "Customer",
      render: (row) => (
        <div className="kit-inline">
          <div>{row?.name || "?"}</div>
          <Link to={`/customers/${row?.id}`}>
            <Button variant="ghost" type="button">
              View
            </Button>
          </Link>
        </div>
      ),
    },
    { key: "email", header: "Email" },
    { key: "phone", header: "Phone" },
    {
      key: "balance",
      header: "Balance",
      render: (row) => <StatusPill tone={balanceTone(row?.balance)}>{money(row?.balance)}</StatusPill>,
    },
  ];

  if (isLoading) {
    return (
      <Card title="Customers">
        <div className="portalGrid">
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card title="Customers">
        <StatusPill tone="danger">{error?.message || "Failed to load customers"}</StatusPill>
      </Card>
    );
  }

  return (
    <Card title="Customers" headerRight={<StatusPill tone="info">Sorted by balance (DESC)</StatusPill>}>
      {clients.length === 0 ? <StatusPill tone="info">No customers</StatusPill> : <Table keyField="id" columns={columns} rows={clients} />}
    </Card>
  );
};

export default Clients;
