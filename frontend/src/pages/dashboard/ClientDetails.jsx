import React, { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useClientDetails } from "../../hooks/useClientDetails.js";
import { useRecordClientPayment } from "../../hooks/useRecordClientPayment.js";
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

const splitBalance = (balance) => {
  const n = Number(balance);
  if (Number.isNaN(n) || n === 0) return { owed: 0, dueToCustomer: 0 };
  if (n > 0) return { owed: n, dueToCustomer: 0 };
  return { owed: 0, dueToCustomer: Math.abs(n) };
};

const ClientDetails = () => {
  const { id } = useParams();
  const { clientQuery, statementQuery } = useClientDetails(id);
  const recordPayment = useRecordClientPayment();

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ amount: "", method: "cash", reference: "", paid_at: "" });

  const client = clientQuery.data;
  const statement = statementQuery.data?.data;
  const lines = Array.isArray(statement?.lines) ? statement.lines : [];

  const balance = client?.balance ?? statement?.closing_balance ?? 0;
  const { owed, dueToCustomer } = splitBalance(balance);

  const timelineRows = useMemo(() => {
    const normalized = lines.map((l, idx) => ({
      key: `${l?.line_id || idx}`,
      date: l?.date,
      description: l?.description,
      debit: l?.debit,
      credit: l?.credit,
      running_balance: l?.running_balance,
      reference_type: l?.reference_type,
      reference_id: l?.reference_id,
    }));
    return normalized.slice().reverse();
  }, [lines]);

  const columns = [
    { key: "date", header: "Date" },
    { key: "description", header: "Description", render: (row) => row.description || "?" },
    { key: "debit", header: "Debit", render: (row) => money(row.debit) },
    { key: "credit", header: "Credit", render: (row) => money(row.credit) },
    {
      key: "running_balance",
      header: "Running",
      render: (row) => <StatusPill tone="info">{money(row.running_balance)}</StatusPill>,
    },
    { key: "reference_type", header: "Ref Type" },
    { key: "reference_id", header: "Ref ID" },
  ];

  const isLoading = clientQuery.isLoading || statementQuery.isLoading;
  const error = clientQuery.error || statementQuery.error;

  const canSubmit = !recordPayment.isPending && Number(form.amount) > 0 && Boolean(form.method);

  const submit = async () => {
    await recordPayment.mutateAsync({
      customer_id: id,
      amount: Number(form.amount),
      method: form.method,
      reference: form.reference || null,
      paid_at: form.paid_at || null,
      invoice_id: null,
    });
    setModalOpen(false);
    setForm({ amount: "", method: "cash", reference: "", paid_at: "" });
  };

  return (
    <div className="portalGrid">
      <Card
        title="Customer"
        headerRight={
          <div className="kit-inline">
            <Link to="/customers">
              <Button variant="ghost" type="button">
                Back
              </Button>
            </Link>
            <Button type="button" onClick={() => setModalOpen(true)}>
              Record Payment
            </Button>
          </div>
        }
      >
        {isLoading ? (
          <div className="portalGrid">
            <Skeleton className="kit-skeletonLg" />
            <Skeleton className="kit-skeletonLg" />
          </div>
        ) : error ? (
          <StatusPill tone="danger">{error?.message || "Failed to load customer"}</StatusPill>
        ) : (
          <div className="kit-kv">
            <div className="kit-kvItem">
              <div className="kit-muted">Name</div>
              <div className="kit-cardTitle">{client?.name || "?"}</div>
            </div>
            <div className="kit-kvItem">
              <div className="kit-muted">Balance owed by customer</div>
              <div className="kit-cardTitle">{money(owed)}</div>
            </div>
            <div className="kit-kvItem">
              <div className="kit-muted">Balance due to customer</div>
              <div className="kit-cardTitle">{money(dueToCustomer)}</div>
            </div>
          </div>
        )}
      </Card>

      <Card title="Timeline">
        {isLoading ? (
          <div className="portalGrid">
            <Skeleton className="kit-skeletonLg" />
            <Skeleton className="kit-skeletonLg" />
            <Skeleton className="kit-skeletonLg" />
          </div>
        ) : timelineRows.length === 0 ? (
          <StatusPill tone="info">No ledger activity</StatusPill>
        ) : (
          <Table keyField="key" columns={columns} rows={timelineRows} />
        )}
      </Card>

      <Modal
        open={modalOpen}
        title="Record Payment"
        onClose={() => setModalOpen(false)}
        actions={
          <div className="kit-formActions">
            <Button variant="ghost" type="button" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="button" disabled={!canSubmit} onClick={submit}>
              {recordPayment.isPending ? "Saving..." : "Save"}
            </Button>
          </div>
        }
      >
        {recordPayment.error ? (
          <div className="portalGrid">
            <StatusPill tone="danger">{recordPayment.error?.message || "Failed to save"}</StatusPill>
          </div>
        ) : null}
        <div className="kit-form">
          <div className="kit-formRow">
            <div className="kit-label">Amount</div>
            <input
              className="kit-input"
              value={form.amount}
              onChange={(e) => setForm((p) => ({ ...p, amount: e.target.value }))}
              inputMode="decimal"
              placeholder="0.00"
            />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Method</div>
            <select className="kit-input" value={form.method} onChange={(e) => setForm((p) => ({ ...p, method: e.target.value }))}>
              <option value="cash">cash</option>
              <option value="bank">bank</option>
              <option value="wallet">wallet</option>
            </select>
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Reference</div>
            <input
              className="kit-input"
              value={form.reference}
              onChange={(e) => setForm((p) => ({ ...p, reference: e.target.value }))}
              placeholder="Optional"
            />
          </div>
          <div className="kit-formRow">
            <div className="kit-label">Paid at</div>
            <input
              className="kit-input"
              value={form.paid_at}
              onChange={(e) => setForm((p) => ({ ...p, paid_at: e.target.value }))}
              placeholder="YYYY-MM-DDTHH:MM:SS (optional)"
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default ClientDetails;
