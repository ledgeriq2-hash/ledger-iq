import React from "react";
import { Link } from "react-router-dom";

import { useClients, useCreateCustomer } from "../../hooks/useClients.js";
import Button from "../../components/kit/Button.jsx";
import Card from "../../components/kit/Card.jsx";
import Modal from "../../components/kit/Modal.jsx";
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

const initialForm = {
  code: "",
  name: "",
  email: "",
  phone: "",
  tax_id: "",
};

const Clients = () => {
  const { data, isLoading, error } = useClients({ page: 1, pageSize: 100 });
  const createCustomer = useCreateCustomer();
  const clients = data?.items || [];
  const [modalOpen, setModalOpen] = React.useState(false);
  const [formState, setFormState] = React.useState(initialForm);

  const closeModal = () => {
    setModalOpen(false);
    setFormState(initialForm);
  };

  const canSubmit =
    Boolean(formState.code?.trim()) &&
    Boolean(formState.name?.trim()) &&
    !createCustomer.isPending;

  const submitForm = async () => {
    if (!canSubmit) return;
    const payload = {
      code: formState.code.trim(),
      name: formState.name.trim(),
      email: formState.email?.trim() || null,
      phone: formState.phone?.trim() || null,
      tax_id: formState.tax_id?.trim() || null,
    };
    try {
      await createCustomer.mutateAsync(payload);
      closeModal();
    } catch {
      // handled via StatusPill
    }
  };

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
    <Card
      title="Customers"
      headerRight={
        <div className="kit-inline">
          <StatusPill tone="info">Sorted by balance (DESC)</StatusPill>
          <Button type="button" variant="secondary" onClick={() => setModalOpen(true)}>
            Add customer
          </Button>
        </div>
      }
    >
      {clients.length === 0 ? <StatusPill tone="info">No customers</StatusPill> : <Table keyField="id" columns={columns} rows={clients} />}

      <Modal
        open={modalOpen}
        title="New Customer"
        onClose={closeModal}
        actions={
          <div className="kit-formActions">
            <Button variant="ghost" type="button" onClick={closeModal}>
              Cancel
            </Button>
            <Button type="button" disabled={!canSubmit} onClick={submitForm}>
              {createCustomer.isPending ? "Saving..." : "Create"}
            </Button>
          </div>
        }
      >
        {createCustomer.error ? (
          <StatusPill tone="danger">{createCustomer.error?.message || "Failed to save customer"}</StatusPill>
        ) : null}
        <div className="kit-form">
          <div className="kit-formRow">
            <div className="kit-label">Code</div>
            <input className="kit-input" value={formState.code} onChange={(event) => setFormState((prev) => ({ ...prev, code: event.target.value }))} />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Name</div>
            <input className="kit-input" value={formState.name} onChange={(event) => setFormState((prev) => ({ ...prev, name: event.target.value }))} />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Email</div>
            <input className="kit-input" value={formState.email} onChange={(event) => setFormState((prev) => ({ ...prev, email: event.target.value }))} />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Phone</div>
            <input className="kit-input" value={formState.phone} onChange={(event) => setFormState((prev) => ({ ...prev, phone: event.target.value }))} />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Tax ID</div>
            <input className="kit-input" value={formState.tax_id} onChange={(event) => setFormState((prev) => ({ ...prev, tax_id: event.target.value }))} />
          </div>
        </div>
      </Modal>
    </Card>
  );
};

export default Clients;
