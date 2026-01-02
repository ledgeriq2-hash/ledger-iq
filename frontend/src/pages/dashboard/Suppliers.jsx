import React, { useMemo, useState } from "react";

import { useCreateSupplier, useDeleteSupplier, useSuppliers, useUpdateSupplier } from "../../hooks/useSuppliers.js";
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
};

const Suppliers = () => {
  const suppliersQuery = useSuppliers();
  const createSupplier = useCreateSupplier();
  const updateSupplier = useUpdateSupplier();
  const deleteSupplier = useDeleteSupplier();

  const [modalState, setModalState] = useState({ open: false, mode: "create", supplier: null });
  const [formState, setFormState] = useState(initialForm);
  const [deletingId, setDeletingId] = useState(null);

  const suppliers = suppliersQuery.data?.items || [];

  const rows = useMemo(
    () =>
      suppliers.map((supplier) => ({
        key: supplier.id,
        id: supplier.id,
        name: supplier.name,
        email: supplier.email,
        phone: supplier.phone,
        address: supplier.address,
        balance: supplier.balance,
      })),
    [suppliers]
  );

  const closeModal = () => {
    setModalState({ open: false, mode: "create", supplier: null });
    setFormState(initialForm);
  };

  const openCreateModal = () => {
    setFormState(initialForm);
    setModalState({ open: true, mode: "create", supplier: null });
  };

  const openEditModal = (supplier) => {
    setFormState({
      name: supplier.name || "",
      email: supplier.email || "",
      phone: supplier.phone || "",
      address: supplier.address || "",
      tax_id: supplier.tax_id || "",
    });
    setModalState({ open: true, mode: "edit", supplier });
  };

  const modalError = modalState.mode === "create" ? createSupplier.error : updateSupplier.error;
  const isSavingModal = modalState.mode === "create" ? createSupplier.isPending : updateSupplier.isPending;
  const canSubmitForm = Boolean(formState.name?.trim()) && !isSavingModal;

  const submitForm = async () => {
    if (!formState.name?.trim()) return;
    const payload = {
      name: formState.name.trim(),
      email: formState.email?.trim() || null,
      phone: formState.phone?.trim() || null,
      address: formState.address?.trim() || null,
      tax_id: formState.tax_id?.trim() || null,
    };

    try {
      if (modalState.mode === "create") {
        await createSupplier.mutateAsync(payload);
      } else if (modalState.supplier?.id) {
        await updateSupplier.mutateAsync({ supplierId: modalState.supplier.id, payload });
      }
      closeModal();
    } catch {
      // Mutation errors handled via StatusPill
    }
  };

  const handleDelete = async (supplier) => {
    if (!window.confirm("Delete this supplier? This cannot be undone.")) {
      return;
    }
    setDeletingId(supplier.id);
    try {
      await deleteSupplier.mutateAsync(supplier.id);
    } finally {
      setDeletingId(null);
    }
  };

  const columns = [
    { key: "name", header: "Supplier" },
    { key: "email", header: "Email" },
    { key: "phone", header: "Phone" },
    { key: "address", header: "Address" },
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
      key: "actions",
      header: "Actions",
      render: (row) => (
        <div className="kit-inline">
          <Button variant="ghost" type="button" onClick={() => openEditModal(row)}>
            Edit
          </Button>
          <Button variant="ghost" type="button" disabled={deletingId === row.id} onClick={() => handleDelete(row)}>
            {deletingId === row.id ? "Deleting..." : "Delete"}
          </Button>
        </div>
      ),
    },
  ];

  const deleteError = deleteSupplier.error;

  const renderContent = () => {
    if (suppliersQuery.isLoading) {
      return (
        <div className="portalGrid">
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
        </div>
      );
    }

    if (suppliersQuery.error) {
      return <StatusPill tone="danger">{suppliersQuery.error?.message || "Failed to load suppliers"}</StatusPill>;
    }

    if (rows.length === 0) {
      return <StatusPill tone="info">No suppliers yet</StatusPill>;
    }

    return (
      <Table keyField="id" columns={columns} rows={rows} />
    );
  };

  return (
    <div className="portalGrid">
      <Card
        title="Suppliers"
        headerRight={
          <Button type="button" variant="secondary" onClick={openCreateModal}>
            Add supplier
          </Button>
        }
      >
        {deleteError ? <StatusPill tone="danger">{deleteError?.message || "Failed to delete supplier"}</StatusPill> : null}
        {renderContent()}
      </Card>

      <Modal
        open={modalState.open}
        title={modalState.mode === "create" ? "New Supplier" : "Edit Supplier"}
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
        {modalError ? <StatusPill tone="danger">{modalError?.message || "Failed to save supplier"}</StatusPill> : null}
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
        </div>
      </Modal>
    </div>
  );
};

export default Suppliers;
