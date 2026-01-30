import React, { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { useClientDetails } from "../../hooks/useClientDetails.js";
import { usePortalLinks } from "../../hooks/usePortalLinks.js";
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
  const { linksQuery, createLink, revokeLink } = usePortalLinks(id);
  const recordPayment = useRecordClientPayment();

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ amount: "", method: "cash", reference: "", paid_at: "" });
  const [linkForm, setLinkForm] = useState({ expiresInHours: 720 });
  const [generatedLink, setGeneratedLink] = useState(null);
  const [linkCopied, setLinkCopied] = useState(false);
  const [revokingId, setRevokingId] = useState(null);

  const client = clientQuery.data;
  const statement = statementQuery.data?.data;
  const lines = Array.isArray(statement?.lines) ? statement.lines : [];
  const links = Array.isArray(linksQuery.data) ? linksQuery.data : [];

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
  const expiresInHours = Number(linkForm.expiresInHours);
  const isExpiryValid =
    Number.isFinite(expiresInHours) && expiresInHours >= 1 && expiresInHours <= 720;
  const canGenerateLink = isExpiryValid && !createLink.isPending && Boolean(id);

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

  const generateLink = async () => {
    if (!canGenerateLink) return;
    const payload = { expiresInHours };
    const result = await createLink.mutateAsync(payload);
    setGeneratedLink(result);
    setLinkCopied(false);
  };

  const copyLink = async () => {
    const url = generatedLink?.url;
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 1500);
    } catch {
      setLinkCopied(false);
    }
  };

  const revokePortalLink = async (tokenId) => {
    if (!tokenId) return;
    setRevokingId(tokenId);
    try {
      await revokeLink.mutateAsync(tokenId);
    } finally {
      setRevokingId(null);
    }
  };

  const formatDateTime = (value) => {
    if (!value) return "—";
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return String(value);
    return dt.toLocaleString();
  };

  const linkRows = useMemo(() => {
    const now = Date.now();
    return links.map((link) => {
      const expiresAt = link?.expires_at ? new Date(link.expires_at).getTime() : null;
      const revokedAt = link?.revoked_at;
      let status = "Active";
      if (revokedAt) status = "Revoked";
      else if (expiresAt && now > expiresAt) status = "Expired";
      return {
        token_id: link?.token_id,
        created_at: link?.created_at,
        expires_at: link?.expires_at,
        revoked_at: revokedAt,
        status,
        is_used: link?.is_used,
      };
    });
  }, [links]);

  const linkColumns = [
    {
      key: "created_at",
      header: "Created",
      render: (row) => formatDateTime(row.created_at),
    },
    {
      key: "expires_at",
      header: "Expires",
      render: (row) => formatDateTime(row.expires_at),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => {
        const tone = row.status === "Active" ? "success" : row.status === "Expired" ? "warning" : "danger";
        return <StatusPill tone={tone}>{row.status}</StatusPill>;
      },
    },
    {
      key: "actions",
      header: "Actions",
      render: (row) => {
        const isRevoking = revokeLink.isPending && revokingId === row.token_id;
        if (row.status !== "Active") return "—";
        return (
          <Button
            variant="ghost"
            type="button"
            disabled={isRevoking}
            onClick={() => revokePortalLink(row.token_id)}
          >
            {isRevoking ? "Revoking..." : "Revoke"}
          </Button>
        );
      },
    },
  ];

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

      <Card title="Client Share Link">
        <div className="kit-muted" style={{ marginBottom: "0.75rem" }}>
          Generate time-limited access for this customer portal.
        </div>
        {createLink.error ? (
          <div className="portalGrid">
            <StatusPill tone="danger">{createLink.error?.message || "Failed to generate link"}</StatusPill>
          </div>
        ) : null}
        <div className="kit-form">
          <div className="kit-formRow">
            <div className="kit-label">Expiry (hours)</div>
            <input
              className="kit-input"
              type="number"
              min="1"
              max="720"
              value={linkForm.expiresInHours}
              onChange={(e) => setLinkForm((p) => ({ ...p, expiresInHours: e.target.value }))}
            />
            <div className="kit-muted">1 to 720 hours</div>
          </div>
          <div className="kit-formRow">
            <Button type="button" disabled={!canGenerateLink} onClick={generateLink}>
              {createLink.isPending ? "Generating..." : "Generate Link"}
            </Button>
            {!isExpiryValid ? <StatusPill tone="warning">Enter 1 - 720 hours</StatusPill> : null}
          </div>
        </div>

        {generatedLink?.url ? (
          <div className="kit-formRow">
            <div className="kit-label">Latest link</div>
            <div className="kit-inline" style={{ gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
              <span className="kit-muted" style={{ wordBreak: "break-all" }}>
                {generatedLink.url}
              </span>
              <Button variant="ghost" type="button" onClick={copyLink}>
                {linkCopied ? "Copied" : "Copy"}
              </Button>
            </div>
          </div>
        ) : null}

        <div className="kit-label" style={{ marginTop: "1rem" }}>
          Existing links
        </div>
        {linksQuery.isLoading ? (
          <div className="portalGrid">
            <Skeleton className="kit-skeletonLg" />
          </div>
        ) : linksQuery.error ? (
          <StatusPill tone="danger">{linksQuery.error?.message || "Failed to load links"}</StatusPill>
        ) : linkRows.length === 0 ? (
          <StatusPill tone="info">No links generated yet</StatusPill>
        ) : (
          <Table keyField="token_id" columns={linkColumns} rows={linkRows} />
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
