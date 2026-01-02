import React, { useMemo, useState } from "react";

import { useCreateDebt, useDebts, useDeleteDebt, useRecordDebtPayment, useUpdateDebt } from "../../hooks/useDebts.js";
import { useSuppliers } from "../../hooks/useSuppliers.js";
import Button from "../../components/kit/Button.jsx";
import Card from "../../components/kit/Card.jsx";
import Modal from "../../components/kit/Modal.jsx";
import Skeleton from "../../components/kit/Skeleton.jsx";
import StatusPill from "../../components/kit/StatusPill.jsx";
import Table from "../../components/kit/Table.jsx";

const STATUS_TABS = ["all", "open", "partial", "paid", "cancelled", "draft"];

const money = (value) => {
  if (value === null || value === undefined) return "0.00";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toFixed(2);
};

const sumPayments = (payments) =>
  (Array.isArray(payments) ? payments : []).reduce((acc, payment) => acc + Number(payment?.amount || 0), 0);

const initialForm = {
  supplierId: "",
  description: "",
  amount: "",
  currency: "USD",
  dueDate: "",
  status: "open",
};

const initialPaymentForm = {
  amount: "",
  method: "cash",
  reference: "",
  paid_at: "",
};

const Debts = () => {
  const [statusFilter, setStatusFilter] = useState("all");
  const debtsQuery = useDebts({ status: statusFilter, page: 1, pageSize: 200 });
  const suppliersQuery = useSuppliers({ page: 1, pageSize: 200 });
  const createDebt = useCreateDebt();
  const updateDebt = useUpdateDebt();
  const deleteDebt = useDeleteDebt();
  const recordPayment = useRecordDebtPayment();

  const [modalState, setModalState] = useState({ open: false, mode: "create", debt: null });
  const [formState, setFormState] = useState(initialForm);
  const [deletingId, setDeletingId] = useState(null);
  const [paymentModal, setPaymentModal] = useState({ open: false, debtId: null });
  const [paymentForm, setPaymentForm] = useState(initialPaymentForm);

  const suppliers = suppliersQuery.data?.items || [];
  const supplierMap = useMemo(
    () =>
      suppliers.reduce((acc, supplier) => {
        acc[supplier.id] = supplier.name || supplier.email || supplier.id;
        return acc;
      }, {}),
    [suppliers]
  );

  const debts = debtsQuery.data?.items || [];
  const rows = useMemo(
    () =>
      debts.map((debt) => {
        const paid = sumPayments(debt.payments);
        const amountValue = Number(debt.amount) || 0;
        const outstanding = Math.max(0, amountValue - paid);
        return {
          key: debt.id,
          id: debt.id,
          supplier_id: debt.supplier_id,
          description: debt.description,
          amount: amountValue,
          currency: debt.currency,
          status: debt.status,
          due_date: debt.due_date,
          paid,
          outstanding,
        };
      }),
    [debts]
  );

  const closeModal = () => {
    setModalState({ open: false, mode: "create", debt: null });
    setFormState(initialForm);
  };

  const openCreateModal = () => {
    setFormState((prev) => ({
      ...initialForm,
      supplierId: suppliers[0]?.id || "",
      currency: prev.currency,
    }));
    setModalState({ open: true, mode: "create", debt: null });
  };

  const openEditModal = (debt) => {
    if (!debt) return;
    setFormState({
      supplierId: debt.supplier_id || "",
      description: debt.description || "",
      amount: debt.amount ? String(debt.amount) : "",
      currency: debt.currency || "USD",
      dueDate: debt.due_date || "",
      status: debt.status || "open",
    });
    setModalState({ open: true, mode: "edit", debt });
  };

  const modalError = modalState.mode === "create" ? createDebt.error : updateDebt.error;
  const isSavingModal = modalState.mode === "create" ? createDebt.isPending : updateDebt.isPending;
  const canSubmitForm = Boolean(formState.supplierId && Number(formState.amount) > 0 && !isSavingModal);

  const submitForm = async () => {
    if (!canSubmitForm) return;
    const payload = {
      supplier_id: formState.supplierId,
      description: formState.description?.trim() || undefined,
      amount: Number(formState.amount),
      currency: formState.currency || "USD",
      due_date: formState.dueDate || undefined,
      status: formState.status || undefined,
    };
    try {
      if (modalState.mode === "create") {
        await createDebt.mutateAsync(payload);
      } else if (modalState.debt?.id) {
        await updateDebt.mutateAsync({ debtId: modalState.debt.id, payload });
      }
      closeModal();
    } catch {
      // errors surfaced via StatusPill
    }
  };

  const handleDelete = async (debt) => {
    if (!window.confirm("Delete this debt? This cannot be undone.")) return;
    setDeletingId(debt.id);
    try {
      await deleteDebt.mutateAsync(debt.id);
    } finally {
      setDeletingId(null);
    }
  };

  const startPayment = (debt) => {
    setPaymentModal({ open: true, debtId: debt.id });
  };

  const paymentCanSubmit =
    Boolean(paymentModal.debtId) && Number(paymentForm.amount) > 0 && !recordPayment.isPending;

  const submitPayment = async () => {
    if (!paymentModal.debtId || !paymentCanSubmit) return;
    try {
      await recordPayment.mutateAsync({
        debtId: paymentModal.debtId,
        payload: {
          amount: Number(paymentForm.amount),
          method: paymentForm.method,
          reference: paymentForm.reference?.trim() || null,
          paid_at: paymentForm.paid_at || null,
        },
      });
      setPaymentModal({ open: false, debtId: null });
      setPaymentForm(initialPaymentForm);
    } catch {
      // handled by StatusPill
    }
  };

  const statusTone = (status) => {
    const value = String(status || "").toLowerCase();
    if (["paid"].includes(value)) return "success";
    if (["partial", "open", "draft"].includes(value)) return "info";
    if (value === "cancelled") return "danger";
    return "primary";
  };

  const columns = [
    { key: "id", header: "Debt" },
    {
      key: "supplier",
      header: "Supplier",
      render: (row) => supplierMap[row.supplier_id] || row.supplier_id || "Unknown",
    },
    { key: "description", header: "Description" },
    {
      key: "amount",
      header: "Amount",
      render: (row) => (
        <StatusPill tone="info">
          {money(row.amount)} {row.currency || "USD"}
        </StatusPill>
      ),
    },
    {
      key: "paid",
      header: "Paid",
      render: (row) => money(row.paid),
    },
    {
      key: "outstanding",
      header: "Outstanding",
      render: (row) => money(row.outstanding),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusPill tone={statusTone(row.status)}>{row.status || "OPEN"}</StatusPill>,
    },
    { key: "due_date", header: "Due", render: (row) => row.due_date || "—" },
    {
      key: "actions",
      header: "Actions",
      render: (row) => (
        <div className="kit-inline">
          <Button
            variant="ghost"
            type="button"
            disabled={row.outstanding <= 0 || recordPayment.isPending}
            onClick={() => startPayment(row)}
          >
            Record payment
          </Button>
          <Button variant="ghost" type="button" disabled={row.status === "paid"} onClick={() => openEditModal(row)}>
            Edit
          </Button>
          <Button
            variant="ghost"
            type="button"
            disabled={row.status === "paid" || deletingId === row.id}
            onClick={() => handleDelete(row)}
          >
            {deletingId === row.id ? "Deleting..." : "Delete"}
          </Button>
        </div>
      ),
    },
  ];

  const deleteError = deleteDebt.error;

  const renderContent = () => {
    if (debtsQuery.isLoading || suppliersQuery.isLoading) {
      return (
        <div className="portalGrid">
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
        </div>
      );
    }

    if (debtsQuery.error) {
      return <StatusPill tone="danger">{debtsQuery.error?.message || "Failed to load debts"}</StatusPill>;
    }

    if (rows.length === 0) {
      return <StatusPill tone="info">No debts recorded yet</StatusPill>;
    }

    return <Table keyField="id" columns={columns} rows={rows} />;
  };

  return (
    <div className="portalGrid">
      <Card
        title="Debts"
        headerRight={
          <div className="kit-inline">
            {STATUS_TABS.map((tab) => (
              <Button
                key={tab}
                type="button"
                variant={statusFilter === tab ? "primary" : "ghost"}
                onClick={() => setStatusFilter(tab)}
              >
                {tab}
              </Button>
            ))}
            <Button type="button" variant="secondary" onClick={openCreateModal}>
              New debt
            </Button>
          </div>
        }
      >
        {deleteError ? <StatusPill tone="danger">{deleteError?.message || "Failed to delete debt"}</StatusPill> : null}
        {renderContent()}
      </Card>

      <Modal
        open={modalState.open}
        title={modalState.mode === "create" ? "New debt" : "Edit debt"}
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
        {modalError ? <StatusPill tone="danger">{modalError?.message || "Unable to save debt"}</StatusPill> : null}
        {!suppliers.length ? <StatusPill tone="warning">Create a supplier before recording debts.</StatusPill> : null}
        <div className="kit-form">
          <div className="kit-formRow">
            <div className="kit-label">Supplier</div>
            <select
              className="kit-input"
              value={formState.supplierId}
              onChange={(event) => setFormState((prev) => ({ ...prev, supplierId: event.target.value }))}
            >
              <option value="">Select supplier</option>
              {suppliers.map((supplier) => (
                <option key={supplier.id} value={supplier.id}>
                  {supplier.name || supplier.email}
                </option>
              ))}
            </select>
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Description</div>
            <input
              className="kit-input"
              value={formState.description}
              onChange={(event) => setFormState((prev) => ({ ...prev, description: event.target.value }))}
            />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Amount</div>
            <input
              className="kit-input"
              type="number"
              min="0"
              step="0.01"
              value={formState.amount}
              onChange={(event) => setFormState((prev) => ({ ...prev, amount: event.target.value }))}
            />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Currency</div>
            <input
              className="kit-input"
              value={formState.currency}
              onChange={(event) => setFormState((prev) => ({ ...prev, currency: event.target.value }))}
            />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Due date</div>
            <input
              className="kit-input"
              type="date"
              value={formState.dueDate}
              onChange={(event) => setFormState((prev) => ({ ...prev, dueDate: event.target.value }))}
            />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Status</div>
            <select
              className="kit-input"
              value={formState.status}
              onChange={(event) => setFormState((prev) => ({ ...prev, status: event.target.value }))}
            >
              <option value="open">open</option>
              <option value="partial">partial</option>
              <option value="paid">paid</option>
              <option value="cancelled">cancelled</option>
              <option value="draft">draft</option>
            </select>
          </div>
        </div>
      </Modal>

      <Modal
        open={paymentModal.open}
        title="Record payment"
        onClose={() => setPaymentModal({ open: false, debtId: null })}
        actions={
          <div className="kit-formActions">
            <Button variant="ghost" type="button" onClick={() => setPaymentModal({ open: false, debtId: null })}>
              Cancel
            </Button>
            <Button type="button" disabled={!paymentCanSubmit} onClick={submitPayment}>
              {recordPayment.isPending ? "Saving..." : "Save"}
            </Button>
          </div>
        }
      >
        {recordPayment.error ? (
          <StatusPill tone="danger">{recordPayment.error?.message || "Failed to save payment"}</StatusPill>
        ) : null}
        <div className="kit-form">
          <div className="kit-formRow">
            <div className="kit-label">Amount</div>
            <input
              className="kit-input"
              value={paymentForm.amount}
              onChange={(event) => setPaymentForm((prev) => ({ ...prev, amount: event.target.value }))}
              placeholder="0.00"
            />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Method</div>
            <select
              className="kit-input"
              value={paymentForm.method}
              onChange={(event) => setPaymentForm((prev) => ({ ...prev, method: event.target.value }))}
            >
              <option value="cash">cash</option>
              <option value="bank">bank</option>
              <option value="wallet">wallet</option>
            </select>
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Reference</div>
            <input
              className="kit-input"
              value={paymentForm.reference}
              onChange={(event) => setPaymentForm((prev) => ({ ...prev, reference: event.target.value }))}
              placeholder="Optional"
            />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Paid at</div>
            <input
              className="kit-input"
              value={paymentForm.paid_at}
              onChange={(event) => setPaymentForm((prev) => ({ ...prev, paid_at: event.target.value }))}
              placeholder="YYYY-MM-DDTHH:MM:SS (optional)"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default Debts;
