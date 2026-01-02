import React, { useMemo, useState } from "react";

import { useCreateWorker, useDeleteWorker, useUpdateWorker, useWorkers } from "../../hooks/useWorkers.js";
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

const initialForm = {
  name: "",
  email: "",
  phone: "",
  address: "",
  tax_id: "",
  balance: "0",
};

const Workers = () => {
  const workersQuery = useWorkers({ page: 1, pageSize: 100 });
  const createWorker = useCreateWorker();
  const updateWorker = useUpdateWorker();
  const deleteWorker = useDeleteWorker();

  const [modalState, setModalState] = useState({ open: false, mode: "create", worker: null });
  const [formState, setFormState] = useState(initialForm);
  const [deletingId, setDeletingId] = useState(null);

  const closeModal = () => {
    setModalState({ open: false, mode: "create", worker: null });
    setFormState(initialForm);
  };

  const openCreateModal = () => {
    setFormState(initialForm);
    setModalState({ open: true, mode: "create", worker: null });
  };

  const openEditModal = (worker) => {
    if (!worker) return;
    setFormState({
      name: worker.name || "",
      email: worker.email || "",
      phone: worker.phone || "",
      address: worker.address || "",
      tax_id: worker.tax_id || "",
      balance: worker.balance !== undefined ? String(worker.balance) : "0",
    });
    setModalState({ open: true, mode: "edit", worker });
  };

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
        tax_id: worker.tax_id,
        balance: Number(worker.balance) || 0,
        status: worker.is_deleted ? "deleted" : "active",
      })),
    [workers]
  );

  const modalError = modalState.mode === "create" ? createWorker.error : updateWorker.error;
  const isSavingModal = modalState.mode === "create" ? createWorker.isPending : updateWorker.isPending;
  const canSubmitForm = Boolean(formState.name?.trim() && !isSavingModal);

  const submitForm = async () => {
    if (!canSubmitForm) return;
    const payload = {
      name: formState.name?.trim(),
      email: formState.email?.trim() || undefined,
      phone: formState.phone?.trim() || undefined,
      address: formState.address?.trim() || undefined,
      tax_id: formState.tax_id?.trim() || undefined,
      balance: formState.balance ? Number(formState.balance) : undefined,
    };
    try {
      if (modalState.mode === "create") {
        await createWorker.mutateAsync(payload);
      } else if (modalState.worker?.id) {
        await updateWorker.mutateAsync({ workerId: modalState.worker.id, payload });
      }
      closeModal();
    } catch {
      // errors surfaced via StatusPill
    }
  };

  const handleDelete = async (worker) => {
    if (!window.confirm("Delete this worker? This cannot be undone.")) return;
    setDeletingId(worker.id);
    try {
      await deleteWorker.mutateAsync(worker.id);
    } finally {
      setDeletingId(null);
    }
  };

  const statusTone = (status) => {
    if (status === "active") return "success";
    if (status === "deleted") return "danger";
    return "info";
  };

  const columns = [
    { key: "name", header: "Worker" },
    { key: "email", header: "Email" },
    { key: "phone", header: "Phone" },
    { key: "address", header: "Address" },
    { key: "tax_id", header: "Tax ID" },
    {
      key: "balance",
      header: "Balance",
      render: (row) => (
        <StatusPill tone="info">
          {money(row.balance)}
        </StatusPill>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusPill tone={statusTone(row.status)}>{row.status}</StatusPill>,
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) => (
        <div className="kit-inline">
          <Button variant="ghost" type="button" onClick={() => openEditModal(row)}>
            Edit
          </Button>
          <Button
            variant="ghost"
            type="button"
            disabled={deletingId === row.id}
            onClick={() => handleDelete(row)}
          >
            {deletingId === row.id ? "Deleting..." : "Delete"}
          </Button>
        </div>
      ),
    },
  ];

  const deleteError = deleteWorker.error;

  const renderContent = () => {
    if (workersQuery.isLoading) {
      return (
        <div className="portalGrid">
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
        </div>
      );
    }

    if (workersQuery.error) {
      return <StatusPill tone="danger">{workersQuery.error?.message || "Failed to load workers"}</StatusPill>;
    }

    if (rows.length === 0) {
      return <StatusPill tone="info">No workers yet</StatusPill>;
    }

    return <Table keyField="id" columns={columns} rows={rows} />;
  };

  return (
    <div className="portalGrid">
      <Card
        title="Workers"
        headerRight={
          <Button type="button" variant="secondary" onClick={openCreateModal}>
            Add worker
          </Button>
        }
      >
        {deleteError ? <StatusPill tone="danger">{deleteError?.message || "Failed to delete worker"}</StatusPill> : null}
        {renderContent()}
      </Card>

      <Modal
        open={modalState.open}
        title={modalState.mode === "create" ? "New worker" : "Edit worker"}
        onClose={closeModal}
        actions={
          <div className="kit-formActions">
            <Button variant="ghost" type="button" onClick={closeModal}>
              Cancel
            </Button>
            <Button type="button" disabled={!canSubmitForm} onClick={submitForm}>
              {isSavingModal ? "Saving..." : modalState.mode === "create" ? "Create" : "Save"}
            </Button>
          </div>
        }
      >
        {modalError ? <StatusPill tone="danger">{modalError?.message || "Unable to save worker"}</StatusPill> : null}
        <div className="kit-form">
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
          <div className="kit-formRow">
            <div className="kit-label">Balance</div>
            <input
              className="kit-input"
              type="number"
              step="0.01"
              min="0"
              value={formState.balance}
              onChange={(event) => setFormState((prev) => ({ ...prev, balance: event.target.value }))}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default Workers;
