import React, { useMemo, useState } from "react";

import { useCreateWorker, useWorkers } from "../../hooks/useWorkers.js";
import Button from "../../components/kit/Button.jsx";
import Card from "../../components/kit/Card.jsx";
import Modal from "../../components/kit/Modal.jsx";
import Skeleton from "../../components/kit/Skeleton.jsx";
import StatusPill from "../../components/kit/StatusPill.jsx";
import Table from "../../components/kit/Table.jsx";

const initialForm = {
  code: "",
  name: "",
  email: "",
  phone: "",
  address: "",
  tax_id: "",
};

const Employees = () => {
  const workersQuery = useWorkers({ page: 1, pageSize: 100 });
  const createWorker = useCreateWorker();

  const [modalOpen, setModalOpen] = useState(false);
  const [formState, setFormState] = useState(initialForm);

  const workers = workersQuery.data?.items || [];

  const rows = useMemo(
    () =>
      workers.map((worker) => ({
        key: worker.id,
        id: worker.id,
        name: worker.name,
        email: worker.email,
        phone: worker.phone,
        address: worker.address,
        status: worker.status,
      })),
    [workers]
  );

  const closeModal = () => {
    setModalOpen(false);
    setFormState(initialForm);
  };

  const canSubmit =
    Boolean(formState.code?.trim()) &&
    Boolean(formState.name?.trim()) &&
    !createWorker.isPending;

  const submitForm = async () => {
    if (!canSubmit) return;
    const payload = {
      code: formState.code.trim(),
      name: formState.name.trim(),
      email: formState.email?.trim() || null,
      phone: formState.phone?.trim() || null,
      address: formState.address?.trim() || null,
      tax_id: formState.tax_id?.trim() || null,
    };
    try {
      await createWorker.mutateAsync(payload);
      closeModal();
    } catch {
      // handled via StatusPill
    }
  };

  const columns = [
    { key: "name", header: "Employee" },
    { key: "email", header: "Email" },
    { key: "phone", header: "Phone" },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusPill tone={row.status === "ACTIVE" ? "success" : "warning"}>{row.status}</StatusPill>,
    },
  ];

  if (workersQuery.isLoading) {
    return (
      <Card title="Employees">
        <div className="portalGrid">
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
        </div>
      </Card>
    );
  }

  if (workersQuery.error) {
    return (
      <Card title="Employees">
        <StatusPill tone="danger">{workersQuery.error?.message || "Failed to load employees"}</StatusPill>
      </Card>
    );
  }

  return (
    <Card
      title="Employees"
      headerRight={
        <Button type="button" variant="secondary" onClick={() => setModalOpen(true)}>
          Add employee
        </Button>
      }
    >
      {rows.length === 0 ? <StatusPill tone="info">No employees yet</StatusPill> : <Table keyField="id" columns={columns} rows={rows} />}

      <Modal
        open={modalOpen}
        title="New Employee"
        onClose={closeModal}
        actions={
          <div className="kit-formActions">
            <Button variant="ghost" type="button" onClick={closeModal}>
              Cancel
            </Button>
            <Button type="button" disabled={!canSubmit} onClick={submitForm}>
              {createWorker.isPending ? "Saving..." : "Create"}
            </Button>
          </div>
        }
      >
        {createWorker.error ? (
          <StatusPill tone="danger">{createWorker.error?.message || "Failed to save employee"}</StatusPill>
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
            <div className="kit-label">Address</div>
            <input className="kit-input" value={formState.address} onChange={(event) => setFormState((prev) => ({ ...prev, address: event.target.value }))} />
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

export default Employees;
