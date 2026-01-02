import React, { useMemo, useState } from "react";

import { useTreasury } from "../../hooks/useTreasury.js";
import Button from "../../components/kit/Button.jsx";
import Card from "../../components/kit/Card.jsx";
import Skeleton from "../../components/kit/Skeleton.jsx";
import StatusPill from "../../components/kit/StatusPill.jsx";
import Table from "../../components/kit/Table.jsx";

const money = (value) => {
  if (value === null || value === undefined) return "0.00";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toFixed(2);
};

const Treasury = () => {
  const [draftFilters, setDraftFilters] = useState({
    from_date: "",
    to_date: "",
    treasury_id: "",
    direction: "",
    reference_type: "",
    reference_id: "",
  });
  const [filters, setFilters] = useState(draftFilters);

  const { data, isLoading, error } = useTreasury(filters);
  const report = data?.data || {};
  const transactions = Array.isArray(report?.transactions) ? report.transactions : [];

  const totals = report?.totals || {};

  const rows = useMemo(
    () =>
      transactions.map((t, idx) => ({
        key: `${t?.id || idx}`,
        created_at: t?.created_at,
        treasury_id: t?.treasury_id,
        direction: t?.direction,
        amount: t?.amount,
        reference_type: t?.reference_type,
        reference_id: t?.reference_id,
      })),
    [transactions]
  );

  const columns = [
    { key: "created_at", header: "When" },
    { key: "treasury_id", header: "Treasury" },
    { key: "direction", header: "Dir", render: (row) => <StatusPill tone={row.direction === "in" ? "success" : "warning"}>{row.direction}</StatusPill> },
    { key: "amount", header: "Amount", render: (row) => money(row.amount) },
    { key: "reference_type", header: "Ref Type" },
    { key: "reference_id", header: "Ref ID" },
  ];

  return (
    <div className="portalGrid">
      <Card
        title="Treasury"
        headerRight={
          <div className="kit-inline">
            <StatusPill tone="info">Movements</StatusPill>
          </div>
        }
      >
        <div className="kit-form">
          <div className="kit-kv">
            <div className="kit-formRow">
              <div className="kit-label">From</div>
              <input className="kit-input" value={draftFilters.from_date} onChange={(e) => setDraftFilters((p) => ({ ...p, from_date: e.target.value }))} placeholder="YYYY-MM-DD" />
            </div>
            <div className="kit-formRow">
              <div className="kit-label">To</div>
              <input className="kit-input" value={draftFilters.to_date} onChange={(e) => setDraftFilters((p) => ({ ...p, to_date: e.target.value }))} placeholder="YYYY-MM-DD" />
            </div>
            <div className="kit-formRow">
              <div className="kit-label">Direction</div>
              <select className="kit-input" value={draftFilters.direction} onChange={(e) => setDraftFilters((p) => ({ ...p, direction: e.target.value }))}>
                <option value="">all</option>
                <option value="in">in</option>
                <option value="out">out</option>
              </select>
            </div>
            <div className="kit-formRow">
              <div className="kit-label">Treasury ID</div>
              <input className="kit-input" value={draftFilters.treasury_id} onChange={(e) => setDraftFilters((p) => ({ ...p, treasury_id: e.target.value }))} placeholder="optional UUID" />
            </div>
            <div className="kit-formRow">
              <div className="kit-label">Reference type</div>
              <input className="kit-input" value={draftFilters.reference_type} onChange={(e) => setDraftFilters((p) => ({ ...p, reference_type: e.target.value }))} placeholder="invoice/payment/expense" />
            </div>
            <div className="kit-formRow">
              <div className="kit-label">Reference ID</div>
              <input className="kit-input" value={draftFilters.reference_id} onChange={(e) => setDraftFilters((p) => ({ ...p, reference_id: e.target.value }))} placeholder="optional UUID" />
            </div>
          </div>
          <div className="kit-formActions">
            <Button variant="ghost" type="button" onClick={() => { setDraftFilters({ from_date: "", to_date: "", treasury_id: "", direction: "", reference_type: "", reference_id: "" }); setFilters({ from_date: "", to_date: "", treasury_id: "", direction: "", reference_type: "", reference_id: "" }); }}>
              Reset
            </Button>
            <Button type="button" onClick={() => setFilters(draftFilters)}>
              Apply
            </Button>
          </div>
        </div>
      </Card>

      <Card title="Totals">
        {isLoading ? (
          <div className="portalGrid">
            <Skeleton className="kit-skeletonLg" />
          </div>
        ) : error ? (
          <StatusPill tone="danger">{error?.message || "Failed to load treasury report"}</StatusPill>
        ) : (
          <div className="kit-kv">
            <div className="kit-kvItem">
              <div className="kit-muted">In</div>
              <div className="kit-cardTitle">{money(totals?.in)}</div>
            </div>
            <div className="kit-kvItem">
              <div className="kit-muted">Out</div>
              <div className="kit-cardTitle">{money(totals?.out)}</div>
            </div>
            <div className="kit-kvItem">
              <div className="kit-muted">Net</div>
              <div className="kit-cardTitle">{money(totals?.net)}</div>
            </div>
          </div>
        )}
      </Card>

      <Card title="Movements">
        {isLoading ? (
          <div className="portalGrid">
            <Skeleton className="kit-skeletonLg" />
            <Skeleton className="kit-skeletonLg" />
            <Skeleton className="kit-skeletonLg" />
          </div>
        ) : rows.length === 0 ? (
          <StatusPill tone="info">No transactions</StatusPill>
        ) : (
          <Table keyField="key" columns={columns} rows={rows} />
        )}
      </Card>
    </div>
  );
};

export default Treasury;

