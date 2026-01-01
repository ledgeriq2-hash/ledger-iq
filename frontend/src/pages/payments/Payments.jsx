import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import Button from "../../components/ui/Button.jsx";
import Card from "../../components/ui/Card.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";
import LoadingSkeleton from "../../components/ui/LoadingSkeleton.jsx";
import Table from "../../components/kit/Table.jsx";
import { useClients } from "../../hooks/useClients.js";
import { usePayments } from "../../hooks/usePayments.js";
import { useRecordClientPayment } from "../../hooks/useRecordClientPayment.js";
import { useTreasury } from "../../hooks/useTreasury.js";

const formatMoney = (value, currency = "USD") => {
  const number = Number(value);
  if (!Number.isFinite(number)) return "N/A";
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(number);
};

const formatDateTime = (value) => {
  if (!value) return "N/A";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
};

const toNumber = (value) => {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

const Payments = () => {
  const navigate = useNavigate();
  const paymentsQuery = usePayments();
  const clientsQuery = useClients();
  const treasuryQuery = useTreasury();
  const recordPayment = useRecordClientPayment();

  const [formOpen, setFormOpen] = useState(false);
  const [paymentType, setPaymentType] = useState("receipt");
  const [formState, setFormState] = useState({
    customer_id: "",
    amount: "",
    method: "",
    reference: "",
  });
  const [formError, setFormError] = useState("");

  const payments = Array.isArray(paymentsQuery.data?.items) ? paymentsQuery.data.items : [];
  const customers = Array.isArray(clientsQuery.data?.items) ? clientsQuery.data.items : [];

  const customerMap = useMemo(
    () =>
      new Map(
        customers.map((customer) => [
          customer.id,
          customer.name || customer.display_name || customer.email || customer.id,
        ])
      ),
    [customers]
  );

  const treasuryRoot = treasuryQuery.data?.data ?? treasuryQuery.data ?? {};
  const treasuryTotals = treasuryRoot?.totals ?? treasuryRoot?.summary ?? {};
  const currency = treasuryRoot?.currency || "USD";
  const treasuryBalance = toNumber(treasuryTotals?.net ?? treasuryTotals?.balance);

  const resetForm = () => {
    setPaymentType("receipt");
    setFormState({ customer_id: "", amount: "", method: "", reference: "" });
    setFormError("");
  };

  const openForm = () => {
    resetForm();
    setFormOpen(true);
  };

  const closeForm = () => {
    setFormOpen(false);
    setFormError("");
  };

  const updateField = (field) => (event) => {
    setFormState((prev) => ({ ...prev, [field]: event.target.value }));
  };

  const amountValue = toNumber(formState.amount);
  const canSubmit =
    paymentType === "receipt" &&
    !recordPayment.isPending &&
    Boolean(formState.customer_id) &&
    Boolean(formState.method) &&
    amountValue !== null &&
    amountValue > 0;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");

    if (paymentType !== "receipt") {
      setFormError("Disbursements are coming soon.");
      return;
    }

    if (!canSubmit) {
      setFormError("Complete the required fields to continue.");
      return;
    }

    if (amountValue === null || amountValue <= 0) {
      setFormError("Enter a valid amount to continue.");
      return;
    }

    const payload = {
      customer_id: formState.customer_id,
      amount: amountValue,
      method: formState.method,
    };

    if (formState.reference.trim()) {
      payload.reference = formState.reference.trim();
    }

    try {
      await recordPayment.mutateAsync(payload);
      await paymentsQuery.refetch();
      closeForm();
    } catch (err) {
      setFormError(err?.message || "Failed to record payment.");
    }
  };

  const columns = [
    {
      key: "reference",
      header: "Payment",
      render: (row) => row.reference || row.id || "N/A",
    },
    {
      key: "customer_id",
      header: "Customer",
      render: (row) => customerMap.get(row.customer_id) || row.customer_id || "N/A",
    },
    {
      key: "method",
      header: "Method",
      render: (row) => row.method || "N/A",
    },
    {
      key: "amount",
      header: "Amount",
      render: (row) => formatMoney(row.amount, currency),
    },
    {
      key: "paid_at",
      header: "Paid at",
      render: (row) => formatDateTime(row.paid_at || row.created_at),
    },
  ];

  const renderTreasuryPreview = () => {
    if (treasuryQuery.isLoading) {
      return <LoadingSkeleton variant="card" rows={1} label="Loading treasury preview" />;
    }

    if (treasuryQuery.isError || !treasuryQuery.data) {
      return (
        <div className="u-grid u-gap-2">
          <div className="u-text-muted">Treasury preview available in Treasury page.</div>
          <Button size="sm" onClick={() => navigate("/treasury")}>
            Open Treasury
          </Button>
        </div>
      );
    }

    return (
      <div className="u-grid u-gap-2">
        <div>
          <div className="dashboardMeta">Balance</div>
          {treasuryBalance === null ? (
            <div className="u-text-muted">Not available</div>
          ) : (
            <div className="dashboardKpiValue">{formatMoney(treasuryBalance, currency)}</div>
          )}
        </div>
        <div className="u-flex u-gap-4 u-wrap">
          <div>
            <div className="dashboardMeta">In</div>
            <div className="u-text-muted">
              {treasuryTotals?.in === undefined || treasuryTotals?.in === null
                ? "Not available"
                : formatMoney(treasuryTotals.in, currency)}
            </div>
          </div>
          <div>
            <div className="dashboardMeta">Out</div>
            <div className="u-text-muted">
              {treasuryTotals?.out === undefined || treasuryTotals?.out === null
                ? "Not available"
                : formatMoney(treasuryTotals.out, currency)}
            </div>
          </div>
          <div>
            <div className="dashboardMeta">Net</div>
            <div className="u-text-muted">
              {treasuryTotals?.net === undefined || treasuryTotals?.net === null
                ? "Not available"
                : formatMoney(treasuryTotals.net, currency)}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="u-grid u-gap-5" data-testid="payments-root">
      <section className="u-flex u-justify-between u-items-center u-gap-3">
        <div>
          <h1 className="u-m-0">Payments</h1>
          <p className="u-text-muted u-m-0">
            Record receipts and review payment activity for the selected company.
          </p>
        </div>
        <Button onClick={openForm}>Record payment</Button>
      </section>

      <Card title="Recent payments" subtitle="Read-only list of recent receipts">
        {paymentsQuery.isLoading ? (
          <LoadingSkeleton variant="table" rows={6} label="Loading payments" />
        ) : paymentsQuery.isError ? (
          <ErrorState
            title="Failed to load payments"
            error={paymentsQuery.error}
            onRetry={paymentsQuery.refetch}
          />
        ) : payments.length === 0 ? (
          <EmptyState
            title="No payments yet"
            message="Record a receipt to start building a payment history."
            actionLabel="Record payment"
            onAction={openForm}
          />
        ) : (
          <Table keyField="id" columns={columns} rows={payments} />
        )}
      </Card>

      {formOpen && (
        <div
          role="dialog"
          aria-modal="true"
          onClick={closeForm}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.45)",
            display: "flex",
            justifyContent: "flex-end",
            zIndex: 40,
          }}
        >
          <div
            onClick={(event) => event.stopPropagation()}
            style={{
              width: "100%",
              maxWidth: "480px",
              height: "100%",
              background: "var(--color-card)",
              boxShadow: "var(--shadow-2)",
              padding: "var(--space-5)",
              overflowY: "auto",
            }}
          >
            <div className="u-flex u-justify-between u-items-center u-gap-3">
              <div>
                <div className="dashboardMeta">Record payment</div>
                <div className="dashboardKpiValue">Receipt intake</div>
              </div>
              <Button variant="ghost" onClick={closeForm}>
                Close
              </Button>
            </div>

            <form className="u-grid u-gap-4 u-pad-3" onSubmit={handleSubmit}>
              <div className="kit-form">
                <div className="kit-formRow">
                  <div className="kit-label">Type</div>
                  <div className="u-flex u-gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant={paymentType === "receipt" ? "primary" : "secondary"}
                      onClick={() => setPaymentType("receipt")}
                    >
                      Receipt
                    </Button>
                    <Button type="button" size="sm" variant="secondary" disabled>
                      Disbursement (Coming soon)
                    </Button>
                  </div>
                </div>

                <div className="kit-formRow">
                  <div className="kit-label">Party</div>
                  {paymentType === "receipt" ? (
                    <select
                      className="kit-input"
                      value={formState.customer_id}
                      onChange={updateField("customer_id")}
                      disabled={clientsQuery.isLoading}
                    >
                      <option value="">
                        {clientsQuery.isLoading ? "Loading customers..." : "Select customer"}
                      </option>
                      {customers.map((customer) => (
                        <option key={customer.id} value={customer.id}>
                          {customer.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="u-grid u-gap-2">
                      <select className="kit-input" disabled>
                        <option>Supplier (Coming soon)</option>
                      </select>
                      <select className="kit-input" disabled>
                        <option>Employee (Coming soon)</option>
                      </select>
                    </div>
                  )}
                  {clientsQuery.isError ? (
                    <div className="u-text-muted">Unable to load customers.</div>
                  ) : null}
                </div>

                <div className="kit-formRow">
                  <div className="kit-label">Amount</div>
                  <input
                    className="kit-input"
                    inputMode="decimal"
                    placeholder="0.00"
                    value={formState.amount}
                    onChange={updateField("amount")}
                    style={{ fontSize: "1.1rem" }}
                  />
                </div>

                <div className="kit-formRow">
                  <div className="kit-label">Method</div>
                  <input
                    className="kit-input"
                    placeholder="Bank transfer, card, cash"
                    value={formState.method}
                    onChange={updateField("method")}
                  />
                </div>

                <div className="kit-formRow">
                  <div className="kit-label">Reference (optional)</div>
                  <input
                    className="kit-input"
                    placeholder="Invoice, memo, or note"
                    value={formState.reference}
                    onChange={updateField("reference")}
                  />
                </div>

                <div className="kit-formRow">
                  <div className="kit-label">Treasury preview</div>
                  {renderTreasuryPreview()}
                </div>
              </div>

              {formError ? <ErrorState compact title="Unable to save" message={formError} /> : null}

              <div className="u-flex u-justify-end u-gap-2">
                <Button type="button" variant="ghost" onClick={closeForm}>
                  Cancel
                </Button>
                <Button type="submit" disabled={!canSubmit}>
                  {recordPayment.isPending ? "Saving..." : "Record payment"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Payments;
