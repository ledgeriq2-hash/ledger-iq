import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useClients } from "../../hooks/useClients.js";
import {
  useInvoices,
  useCreateInvoice,
  useUpdateInvoice,
  useDeleteInvoice,
  usePostInvoice,
  useRecordInvoicePayment,
} from "../../hooks/useInvoices.js";
import Button from "../../components/ui/Button.jsx";
import Card from "../../components/ui/Card.jsx";
import Dialog from "../../components/ui/Dialog.jsx";
import DropdownMenu from "../../components/ui/DropdownMenu.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import Input from "../../components/ui/Input.jsx";
import LoadingSkeleton from "../../components/ui/LoadingSkeleton.jsx";
import Modal from "../../components/ui/Modal.jsx";
import ToggleGroup from "../../components/ui/ToggleGroup.jsx";
import StatusPill from "../../components/kit/StatusPill.jsx";
import Table from "../../components/kit/Table.jsx";
import useNotifications from "../../hooks/useNotifications.js";

const STATUS_TABS = ["all", "draft", "sent", "posted", "partial", "paid", "overdue", "cancelled"];

const STATUS_LABELS = {
  all: "All",
  draft: "Draft",
  sent: "Sent",
  posted: "Posted",
  partial: "Partial",
  paid: "Paid",
  overdue: "Overdue",
  cancelled: "Cancelled",
};

const SUMMARY_STATUS_CONFIG = [
  { key: "draft", label: "Draft" },
  { key: "sent", label: "Sent" },
  { key: "overdue", label: "Overdue" },
  { key: "paid", label: "Paid" },
];

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

const formatDate = (value) => {
  if (!value) return "—";
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) return "—";
  return timestamp.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
};

const getInvoiceLabel = (invoice) => {
  if (!invoice) return "Invoice";
  const candidate = (invoice.invoice_number || invoice.invoiceNumber || "").toString().trim();
  if (candidate) return candidate;
  const shortId = invoice.short_id || invoice.shortId;
  if (shortId) return `INV-${shortId}`;
  if (invoice.id) return `INV-${invoice.id.slice(0, 8)}`;
  return "Invoice";
};

const extractApiError = (error) => {
  const response = error?.response;
  if (response) {
    return {
      status: response.status,
      code: response.data?.code,
      message: response.data?.message || response.statusText || error.message,
    };
  }
  return {
    status: error?.status,
    code: error?.code,
    message: error?.message,
  };
};

const Invoices = () => {
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const invoicesQuery = useInvoices({ page: 1, pageSize: 100, status: statusFilter });
  const summaryQuery = useInvoices({ page: 1, pageSize: 100, status: "all" });
  const customersQuery = useClients({ page: 1, pageSize: 100 });

  const createInvoice = useCreateInvoice();
  const updateInvoice = useUpdateInvoice();
  const deleteInvoice = useDeleteInvoice();
  const postInvoice = usePostInvoice();
  const recordPayment = useRecordInvoicePayment();
  const navigate = useNavigate();
  const { addNotification } = useNotifications();

  const [modalState, setModalState] = useState({ open: false, mode: "create", invoice: null });
  const [formState, setFormState] = useState(initialForm);
  const [items, setItems] = useState([emptyItem()]);
  const [deletingId, setDeletingId] = useState(null);
  const [mappingDialog, setMappingDialog] = useState({ open: false, invoiceId: null, description: "" });
  const [paymentModal, setPaymentModal] = useState({ open: false, invoiceId: null });
  const [paymentForm, setPaymentForm] = useState({ amount: "", method: "cash", reference: "", paid_at: "" });
  const [deleteDialog, setDeleteDialog] = useState({ open: false, invoice: null });

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
  const summaryInvoices = summaryQuery.data?.items || [];
  const rows = useMemo(
    () =>
      invoices.map((invoice) => {
        const label = getInvoiceLabel(invoice);
        const reference = invoice.short_id || invoice.shortId || invoice.id?.slice(0, 8) || "";
        return {
          key: invoice.id,
          id: invoice.id,
          invoice,
          customer_id: invoice.customer_id,
          customerName: customerMap[invoice.customer_id] || invoice.customer_id || "Unknown",
          invoiceLabel: label,
          invoiceReference: reference,
          issue_date: invoice.issue_date,
          due_date: invoice.due_date,
          currency: invoice.currency,
          total_amount: invoice.total_amount,
          status: invoice.status,
        };
      }),
    [invoices, customerMap]
  );

  const filteredRows = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return rows;
    return rows.filter((row) => {
      const label = row.invoiceLabel || "";
      const customer = row.customerName || "";
      return label.toLowerCase().includes(query) || customer.toLowerCase().includes(query);
    });
  }, [rows, searchQuery]);

  const summaryStats = useMemo(() => {
    const accumulator = SUMMARY_STATUS_CONFIG.reduce((acc, item) => {
      acc[item.key] = { count: 0, total: 0, currencies: new Set() };
      return acc;
    }, {});
    summaryInvoices.forEach((invoice) => {
      const statusKey = (invoice.status || "").toLowerCase();
      if (!accumulator[statusKey]) return;
      const amount = Number(invoice.total_amount) || 0;
      accumulator[statusKey].count += 1;
      accumulator[statusKey].total += amount;
      if (invoice.currency) {
        accumulator[statusKey].currencies.add(invoice.currency);
      }
    });
    return SUMMARY_STATUS_CONFIG.map((item) => {
      const stat = accumulator[item.key];
      const singleCurrency = stat.currencies.size === 1 ? Array.from(stat.currencies)[0] : null;
      return {
        key: item.key,
        label: item.label,
        count: stat.count,
        amount:
          stat.count && singleCurrency
            ? `${money(stat.total)} ${singleCurrency}`
            : stat.count
            ? money(stat.total)
            : null,
      };
    });
  }, [summaryInvoices]);

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

  const openDeleteDialog = (invoice) => {
    if (!invoice || String(invoice.status || "").toLowerCase() !== "draft") return;
    setDeleteDialog({ open: true, invoice });
  };

  const closeDeleteDialog = () => {
    setDeleteDialog({ open: false, invoice: null });
  };

  const handleDeleteConfirm = async () => {
    const invoice = deleteDialog.invoice;
    if (!invoice) return;
    setDeletingId(invoice.id);
    try {
      await deleteInvoice.mutateAsync(invoice.id);
      closeDeleteDialog();
    } finally {
      setDeletingId(null);
    }
  };

  const closeMappingDialog = () => setMappingDialog({ open: false, invoiceId: null, description: "" });

  const handlePostError = (error, invoiceId) => {
    const { status, code, message } = extractApiError(error);
    if (status === 422 && code === "account_mapping_missing") {
      setMappingDialog({
        open: true,
        invoiceId,
        description: message || "Account mapping is missing required keys, so this invoice cannot be posted until the mapping is configured.",
      });
      return;
    }
    addNotification({
      title: "Unable to post invoice",
      message: message || "Something went wrong. Please try again.",
    });
  };

  // Must await to avoid unhandled promise rejection from the mutation.
  const handlePost = async (invoiceId) => {
    if (!invoiceId) return;
    try {
      await postInvoice.mutateAsync(invoiceId);
    } catch (error) {
      handlePostError(error, invoiceId);
    }
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
    {
      key: "invoice",
      header: "Invoice",
      render: (row) => (
        <div className="invoiceCell">
          <div className="invoiceLabel">{row.invoiceLabel}</div>
          {row.invoiceReference ? <div className="invoiceReference">#{row.invoiceReference}</div> : null}
        </div>
      ),
    },
    {
      key: "customer",
      header: "Customer",
      render: (row) => row.customerName,
    },
    {
      key: "issue_date",
      header: "Issue",
      render: (row) => formatDate(row.issue_date),
    },
    {
      key: "due_date",
      header: "Due",
      render: (row) => formatDate(row.due_date),
    },
    {
      key: "total_amount",
      header: "Total",
      render: (row) => {
        const value = `${money(row.total_amount)} ${row.currency || ""}`.trim();
        return value || "—";
      },
    },
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
        const disableDelete = !isDraft || deleteInvoice.isPending;
        const disableEdit = !isDraft;
        return (
          <div className="rowActions">
              {isDraft ? (
                <Button
                  variant="primary"
                  size="sm"
                  type="button"
                  disabled={postInvoice.isPending}
                  onClick={async () => await handlePost(row.id)}
                >
                  {postInvoice.isPending ? "Posting..." : "Post"}
                </Button>
              ) : null}
            <DropdownMenu
              items={[
                {
                  key: "recordPayment",
                  label: "Record payment",
                  disabled: !canPay,
                  onSelect: () => setPaymentModal({ open: true, invoiceId: row.id }),
                },
                {
                  key: "edit",
                  label: "Edit",
                  disabled: disableEdit,
                  onSelect: () => openEditModal(row.invoice),
                },
                {
                  key: "delete",
                  label: deletingId === row.id && deleteInvoice.isPending ? "Deleting..." : "Delete",
                  disabled: disableDelete,
                  onSelect: () => openDeleteDialog(row.invoice),
                },
              ]}
            />
          </div>
        );
      },
    },
  ];

  const deleteError = deleteInvoice.error;

  const filtersActive = statusFilter !== "all" || Boolean(searchQuery.trim());
  const tableLoading = invoicesQuery.isLoading || customersQuery.isLoading;
  const tableError = invoicesQuery.error;

  const clearFilters = () => {
    if (searchQuery) setSearchQuery("");
    if (statusFilter !== "all") setStatusFilter("all");
  };

  const renderTableContent = () => {
    if (tableError) {
      return <StatusPill tone="danger">{tableError?.message || "Failed to load invoices"}</StatusPill>;
    }

    if (tableLoading) {
      return <LoadingSkeleton variant="table" rows={4} label="Loading invoices" />;
    }

    if (!filteredRows.length) {
      const emptyTitle = summaryInvoices.length ? "No invoices match filters" : "No invoices yet";
      const emptyMessage = summaryInvoices.length
        ? "Try adjusting your search or status filter."
        : "Create your first invoice to get started.";
      return (
        <EmptyState title={emptyTitle} message={emptyMessage} actionLabel="New Invoice" onAction={openCreateModal} compact />
      );
    }

    return <Table keyField="id" columns={columns} rows={filteredRows} />;
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
      <Card className="invoicesCard">
        <div className="invoicesHeader">
          <div>
            <h1 className="invoicesHeaderTitle">Invoices</h1>
            <p className="invoicesSubtitle">Track invoices, payments, and outstanding balances with confidence.</p>
          </div>
          <Button type="button" variant="primary" onClick={openCreateModal}>
            New Invoice
          </Button>
        </div>

        <div className="invoicesSummaryGrid">
          {summaryQuery.isLoading
            ? Array.from({ length: 4 }).map((_, idx) => (
                <div className="summaryCard" key={`loading-${idx}`}>
                  <LoadingSkeleton variant="card" rows={2} />
                </div>
              ))
            : summaryStats.map((stat) => (
                <article className="summaryCard" key={stat.key} data-status={stat.key}>
                  <div className="summaryCardLabel">{stat.label}</div>
                  <div className="summaryCardCount">{stat.count}</div>
                  <div className="summaryCardAmount">{stat.amount ?? "—"}</div>
                  <div className="summaryCardAccent" />
                </article>
              ))}
        </div>

        {summaryQuery.error ? (
          <StatusPill tone="danger">{summaryQuery.error?.message || "Failed to load invoice stats"}</StatusPill>
        ) : null}

        <div className="filtersContainer">
          <div className="filtersTop">
            <div className="searchField">
              <Input
                label="Search invoices"
                placeholder="Search invoice #, customer..."
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
              />
            </div>
            <div className="filtersExtras">
              {filtersActive ? (
                <Button type="button" variant="ghost" size="sm" onClick={clearFilters}>
                  Clear filters
                </Button>
              ) : null}
            </div>
          </div>
          <div className="filtersTabs">
            <ToggleGroup
              options={STATUS_TABS.map((tab) => ({ value: tab, label: STATUS_LABELS[tab] }))}
              value={statusFilter}
              onChange={(value) => setStatusFilter(value)}
            />
          </div>
        </div>

        {deleteError ? <StatusPill tone="danger">{deleteError?.message || "Failed to delete invoice"}</StatusPill> : null}

        <div className="tableWrapper">{renderTableContent()}</div>
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

      <Dialog
        open={deleteDialog.open}
        title="Delete draft invoice"
        description="This draft invoice will be permanently removed."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={handleDeleteConfirm}
        onCancel={closeDeleteDialog}
        loading={deleteInvoice.isPending && Boolean(deletingId)}
      />

      <Dialog
        open={mappingDialog.open}
        title="Account mapping required"
        description={
          mappingDialog.description ||
          "Account mapping is not configured, so posting invoices has been blocked until it is set up."
        }
        confirmLabel="Open Settings"
        cancelLabel="Close"
        confirmVariant="primary"
        onConfirm={() => {
          navigate("/settings");
          closeMappingDialog();
        }}
        onCancel={closeMappingDialog}
      />
    </div>
  );
};

export default Invoices;
