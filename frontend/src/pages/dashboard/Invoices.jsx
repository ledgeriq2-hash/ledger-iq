import React, { useMemo, useState } from "react";

import { useClients } from "../../hooks/useClients.js";
import {
  useInvoices,
  useCreateInvoice,
  useUpdateInvoice,
  useDeleteInvoice,
  usePostInvoice,
  useRecordInvoicePayment,
} from "../../hooks/useInvoices.js";
import Button from "../../components/kit/Button.jsx";
import Card from "../../components/kit/Card.jsx";
import Modal from "../../components/kit/Modal.jsx";
import Skeleton from "../../components/kit/Skeleton.jsx";
import StatusPill from "../../components/kit/StatusPill.jsx";
import Table from "../../components/kit/Table.jsx";

const STATUS_TABS = ["all", "draft", "sent", "posted", "partial", "paid", "overdue", "cancelled"];

const todayISO = () => new Date().toISOString().split("T")[0];

const money = (value) => {
  if (value === null || value === undefined) return "0.00";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toFixed(2);
};

const emptyItem = () => ({
  product_id: "",
  description: "",
  quantity: "1",
  unit_price: "0",
  tax_rate: "0",
});

const hasValidItems = (items) =>
  items.some((item) => {
    const quantity = Number(item.quantity);
    const unitPrice = Number(item.unit_price);
    return quantity > 0 && unitPrice >= 0 && (item.description?.trim() || item.product_id?.trim());
  });

const normalizeItemsForPayload = (items) =>
  items
    .map((item) => ({
      product_id: item.product_id || undefined,
      description: item.description?.trim() || undefined,
      quantity: item.quantity ? String(Number(item.quantity)) : "0",
      unit_price: item.unit_price ? String(Number(item.unit_price)) : "0",
      tax_rate: item.tax_rate ? String(Number(item.tax_rate)) : "0",
    }))
    .filter((item) => (item.description || item.product_id) && Number(item.quantity) > 0);

const initialForm = {
  customerId: "",
  issueDate: todayISO(),
  dueDate: "",
  currency: "USD",
  notes: "",
};

const Invoices = () => {
  const [statusFilter, setStatusFilter] = useState("all");
  const invoicesQuery = useInvoices({ page: 1, pageSize: 200, status: statusFilter });
  const customersQuery = useClients({ page: 1, pageSize: 200 });

  const createInvoice = useCreateInvoice();
  const updateInvoice = useUpdateInvoice();
  const deleteInvoice = useDeleteInvoice();
  const postInvoice = usePostInvoice();
  const recordPayment = useRecordInvoicePayment();

  const [modalState, setModalState] = useState({ open: false, mode: "create", invoice: null });
  const [formState, setFormState] = useState(initialForm);
  const [items, setItems] = useState([emptyItem()]);
  const [deletingId, setDeletingId] = useState(null);
  const [paymentModal, setPaymentModal] = useState({ open: false, invoiceId: null });
  const [paymentForm, setPaymentForm] = useState({ amount: "", method: "cash", reference: "", paid_at: "" });

  const customers = customersQuery.data?.items || [];
  const customerMap = useMemo(
    () =>
      customers.reduce((acc, customer) => {
        acc[customer.id] = customer.name || customer.email || customer.id;
        return acc;
      }, {}),
    [customers]
  );

  const invoices = invoicesQuery.data?.items || [];
  const rows = useMemo(
    () =>
      invoices.map((invoice) => ({
        key: invoice.id,
        id: invoice.id,
        customer_id: invoice.customer_id,
        issue_date: invoice.issue_date,
        due_date: invoice.due_date,
        currency: invoice.currency,
        total_amount: invoice.total_amount,
        status: invoice.status,
      })),
    [invoices]
  );

  const closeModal = () => {
    setModalState({ open: false, mode: "create", invoice: null });
    setFormState(initialForm);
    setItems([emptyItem()]);
  };

  const openCreateModal = () => {
    setFormState((prev) => ({
      ...initialForm,
      customerId: customers[0]?.id || "",
      issueDate: prev.issueDate,
    }));
    setItems([emptyItem()]);
    setModalState({ open: true, mode: "create", invoice: null });
  };

  const openEditModal = (invoice) => {
    if (!invoice) return;
    setFormState({
      customerId: invoice.customer_id || "",
      issueDate: invoice.issue_date || todayISO(),
      dueDate: invoice.due_date || "",
      currency: invoice.currency || "USD",
      notes: invoice.notes || "",
    });
    const rowsFromInvoice =
      Array.isArray(invoice.items) && invoice.items.length
        ? invoice.items.map((item) => ({
            product_id: item.product_id || "",
            description: item.description || "",
            quantity: item.quantity ? String(item.quantity) : "1",
            unit_price: item.unit_price ? String(item.unit_price) : "0",
            tax_rate: item.tax_rate ? String(item.tax_rate) : "0",
          }))
        : [emptyItem()];
    setItems(rowsFromInvoice);
    setModalState({ open: true, mode: "edit", invoice });
  };

  const modalError = modalState.mode === "create" ? createInvoice.error : updateInvoice.error;
  const isSavingModal = modalState.mode === "create" ? createInvoice.isPending : updateInvoice.isPending;
  const hasCustomer = Boolean(formState.customerId);
  const hasItems = hasValidItems(items);
  const canSubmitForm = hasCustomer && hasItems && !isSavingModal;

  const submitForm = async () => {
    if (!canSubmitForm) return;
    const payload = {
      customer_id: formState.customerId,
      issue_date: formState.issueDate,
      due_date: formState.dueDate || undefined,
      currency: formState.currency || "USD",
      notes: formState.notes || undefined,
      items: normalizeItemsForPayload(items),
    };
    if (!payload.items.length) return;
    try {
      if (modalState.mode === "create") {
        await createInvoice.mutateAsync(payload);
      } else if (modalState.invoice?.id) {
        await updateInvoice.mutateAsync({ invoiceId: modalState.invoice.id, payload });
      }
      closeModal();
    } catch {
      // errors surfaced via StatusPill
    }
  };

  const handleDelete = async (invoice) => {
    if (invoice.status?.toLowerCase() !== "draft") return;
    if (!window.confirm("Delete this draft invoice?")) return;
    setDeletingId(invoice.id);
    try {
      await deleteInvoice.mutateAsync(invoice.id);
    } finally {
      setDeletingId(null);
    }
  };

  const handlePost = async (invoiceId) => {
    if (!invoiceId) return;
    await postInvoice.mutateAsync(invoiceId);
  };

  const statusTone = (status) => {
    const value = String(status || "").toLowerCase();
    if (value === "draft" || value === "sent") return "info";
    if (value === "paid") return "success";
    if (value === "partial") return "warning";
    if (value === "overdue") return "danger";
    if (value === "posted") return "primary";
    return "info";
  };

  const columns = [
    { key: "id", header: "Invoice" },
    {
      key: "customer",
      header: "Customer",
      render: (row) => customerMap[row.customer_id] || row.customer_id || "Unknown",
    },
    { key: "issue_date", header: "Issue" },
    { key: "due_date", header: "Due" },
    { key: "total_amount", header: "Total", render: (row) => `${money(row.total_amount)} ${row.currency || ""}`.trim() },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusPill tone={statusTone(row.status)}>{row.status || "UNKNOWN"}</StatusPill>,
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) => {
        const currentStatus = String(row.status || "").toLowerCase();
        const isDraft = currentStatus === "draft";
        const canPay = ["posted", "partial", "overdue"].includes(currentStatus);
        return (
          <div className="kit-inline">
            <Button
              variant={isDraft ? "primary" : "ghost"}
              type="button"
              disabled={!isDraft || postInvoice.isPending}
              onClick={() => handlePost(row.id)}
            >
              {postInvoice.isPending ? "Posting..." : "Post"}
            </Button>
            <Button variant="ghost" type="button" disabled={!canPay} onClick={() => setPaymentModal({ open: true, invoiceId: row.id })}>
              Record payment
            </Button>
            <Button variant="ghost" type="button" disabled={!isDraft} onClick={() => openEditModal(row)}>
              Edit
            </Button>
            <Button variant="ghost" type="button" disabled={!isDraft || deletingId === row.id} onClick={() => handleDelete(row)}>
              {deletingId === row.id ? "Deleting..." : "Delete"}
            </Button>
          </div>
        );
      },
    },
  ];

  const deleteError = deleteInvoice.error;

  const renderContent = () => {
    if (invoicesQuery.isLoading || customersQuery.isLoading) {
      return (
        <div className="portalGrid">
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
        </div>
      );
    }

    if (invoicesQuery.error) {
      return <StatusPill tone="danger">{invoicesQuery.error?.message || "Failed to load invoices"}</StatusPill>;
    }

    if (rows.length === 0) {
      return <StatusPill tone="info">No invoices yet</StatusPill>;
    }

    return <Table keyField="id" columns={columns} rows={rows} />;
  };

  const modalItems = items.map((item, index) => (
    <div className="kit-formRow" key={`${item.description}-${index}`}>
      <input
        className="kit-input"
        placeholder="Description"
        value={item.description}
        onChange={(event) =>
          setItems((prev) => {
            const next = [...prev];
            next[index] = { ...next[index], description: event.target.value };
            return next;
          })
        }
      />
      <input
        className="kit-input"
        placeholder="Quantity"
        type="number"
        min="0"
        step="1"
        value={item.quantity}
        onChange={(event) =>
          setItems((prev) => {
            const next = [...prev];
            next[index] = { ...next[index], quantity: event.target.value };
            return next;
          })
        }
      />
      <input
        className="kit-input"
        placeholder="Unit price"
        type="number"
        min="0"
        step="0.01"
        value={item.unit_price}
        onChange={(event) =>
          setItems((prev) => {
            const next = [...prev];
            next[index] = { ...next[index], unit_price: event.target.value };
            return next;
          })
        }
      />
      <input
        className="kit-input"
        placeholder="Tax rate"
        type="number"
        min="0"
        step="0.01"
        value={item.tax_rate}
        onChange={(event) =>
          setItems((prev) => {
            const next = [...prev];
            next[index] = { ...next[index], tax_rate: event.target.value };
            return next;
          })
        }
      />
      <Button
        variant="ghost"
        type="button"
        onClick={() =>
          setItems((prev) => {
            const next = prev.filter((_, idx) => idx !== index);
            return next.length ? next : [emptyItem()];
          })
        }
      >
        Remove
      </Button>
    </div>
  ));

  const addItemRow = () => setItems((prev) => [...prev, emptyItem()]);

  const paymentCanSubmit =
    Boolean(paymentModal.invoiceId) && Number(paymentForm.amount) > 0 && !recordPayment.isPending;

  const submitPayment = async () => {
    await recordPayment.mutateAsync({
      invoiceId: paymentModal.invoiceId,
      payload: {
        amount: Number(paymentForm.amount),
        method: paymentForm.method,
        reference: paymentForm.reference || null,
        paid_at: paymentForm.paid_at || null,
      },
    });
    setPaymentModal({ open: false, invoiceId: null });
    setPaymentForm({ amount: "", method: "cash", reference: "", paid_at: "" });
  };

  return (
    <div className="portalGrid">
      <Card
        title="Invoices"
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
              New invoice
            </Button>
          </div>
        }
      >
        {deleteError ? <StatusPill tone="danger">{deleteError?.message || "Failed to delete invoice"}</StatusPill> : null}
        {renderContent()}
      </Card>

      <Modal
        open={modalState.open}
        title={modalState.mode === "create" ? "New Invoice" : "Edit Invoice"}
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
        {modalError ? <StatusPill tone="danger">{modalError?.message || "Unable to save invoice"}</StatusPill> : null}
        {!customers.length ? (
          <StatusPill tone="warning">Create a customer before issuing invoices.</StatusPill>
        ) : null}
        <div className="kit-form">
          <div className="kit-formRow">
            <div className="kit-label">Customer</div>
            <select
              className="kit-input"
              value={formState.customerId}
              onChange={(event) => setFormState((prev) => ({ ...prev, customerId: event.target.value }))}
            >
              <option value="">Select customer</option>
              {customers.map((customer) => (
                <option key={customer.id} value={customer.id}>
                  {customer.name || customer.email}
                </option>
              ))}
            </select>
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Issue date</div>
            <input
              className="kit-input"
              type="date"
              value={formState.issueDate}
              onChange={(event) => setFormState((prev) => ({ ...prev, issueDate: event.target.value }))}
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
            <div className="kit-label">Currency</div>
            <input
              className="kit-input"
              value={formState.currency}
              onChange={(event) => setFormState((prev) => ({ ...prev, currency: event.target.value }))}
            />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Notes</div>
            <textarea
              className="kit-input"
              value={formState.notes}
              onChange={(event) => setFormState((prev) => ({ ...prev, notes: event.target.value }))}
            />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Items</div>
            {modalItems}
            <Button variant="ghost" type="button" onClick={addItemRow}>
              Add item
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        open={paymentModal.open}
        title="Record Partial Payment"
        onClose={() => setPaymentModal({ open: false, invoiceId: null })}
        actions={
          <div className="kit-formActions">
            <Button variant="ghost" type="button" onClick={() => setPaymentModal({ open: false, invoiceId: null })}>
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

export default Invoices;
