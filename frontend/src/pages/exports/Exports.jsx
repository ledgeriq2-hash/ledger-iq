import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Button from "../../components/ui/Button.jsx";
import Card from "../../components/ui/Card.jsx";
import DataTable from "../../components/ui/DataTable.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";
import Input from "../../components/ui/Input.jsx";
import Select from "../../components/ui/Select.jsx";
import Skeleton from "../../components/ui/Skeleton.jsx";
import { api } from "../../api/generated/index.js";

const toIsoDate = (value) => {
  const s = String(value || "").trim();
  if (!s) return null;
  return s;
};

const isoWeekKey = (dateString) => {
  const d = new Date(`${dateString}T00:00:00Z`);
  if (Number.isNaN(d.getTime())) return null;

  const date = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((date - yearStart) / 86400000 + 1) / 7);
  const weekStr = String(weekNo).padStart(2, "0");
  return `${date.getUTCFullYear()}-W${weekStr}`;
};

const downloadBlob = (filename, blob) => {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
};

const downloadJson = (filename, data) => {
  downloadBlob(filename, new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
};

const csvEscape = (value) => {
  if (value == null) return "";
  const s = String(value);
  if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
  return s;
};

const downloadCsv = (filename, rows) => {
  const csv = rows.map((row) => row.map(csvEscape).join(",")).join("\n");
  downloadBlob(filename, new Blob([csv], { type: "text/csv;charset=utf-8" }));
};

const Exports = () => {
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [granularity, setGranularity] = useState("month");
  const [txLimit, setTxLimit] = useState(10_000);

  const [revenuePreviewOn, setRevenuePreviewOn] = useState(false);
  const [txPreviewOn, setTxPreviewOn] = useState(false);

  const effectiveGranularity = granularity === "week" ? "day" : granularity;

  const revenueParams = useMemo(() => {
    const params = {
      from_date: toIsoDate(fromDate) || undefined,
      to_date: toIsoDate(toDate) || undefined,
      granularity: effectiveGranularity,
      limit: 20_000,
    };
    return params;
  }, [fromDate, toDate, effectiveGranularity]);

  const txParams = useMemo(() => {
    const params = {
      from_date: toIsoDate(fromDate) || undefined,
      to_date: toIsoDate(toDate) || undefined,
      limit: Number(txLimit) || 10_000,
    };
    return params;
  }, [fromDate, toDate, txLimit]);

  const revenueQuery = useQuery({
    queryKey: ["ml", "exports", "revenue_series", revenueParams],
    enabled: revenuePreviewOn,
    queryFn: () => api.ml.exportRevenueSeries(revenueParams),
    staleTime: 0,
    retry: false,
  });

  const transactionsQuery = useQuery({
    queryKey: ["ml", "exports", "transactions", txParams],
    enabled: txPreviewOn,
    queryFn: () => api.ml.exportTransactions(txParams),
    staleTime: 0,
    retry: false,
  });

  const refreshRevenue = revenueQuery.refetch;
  const refreshTransactions = transactionsQuery.refetch;

  const revenueItemsRaw = revenueQuery.data?.items || [];

  const revenueItems = useMemo(() => {
    if (granularity !== "week") return revenueItemsRaw;
    const buckets = new Map();
    revenueItemsRaw.forEach((p) => {
      const key = isoWeekKey(p?.period);
      if (!key) return;
      const current = buckets.get(key) || 0;
      buckets.set(key, current + Number(p?.revenue || 0));
    });
    return Array.from(buckets.entries())
      .sort((a, b) => String(a[0]).localeCompare(String(b[0])))
      .map(([period, revenue]) => ({ period, revenue }));
  }, [revenueItemsRaw, granularity]);

  const revenuePreviewRows = useMemo(() => revenueItems.slice(0, 50), [revenueItems]);
  const txItems = useMemo(() => (Array.isArray(transactionsQuery.data?.items) ? transactionsQuery.data.items : []), [transactionsQuery.data]);
  const txPreviewRows = useMemo(() => txItems.slice(0, 50), [txItems]);

  const revenueColumns = useMemo(
    () => [
      { header: "Period", accessor: "period" },
      { header: "Revenue", accessor: "revenue", align: "right", cell: (v) => Number(v || 0).toFixed(2) },
    ],
    []
  );

  const txColumns = useMemo(
    () => [
      { header: "Source", accessor: "source" },
      { header: "Event date", accessor: "event_date" },
      { header: "Amount", accessor: "amount", align: "right" },
      { header: "Currency", accessor: "currency", align: "center" },
      { header: "Direction", accessor: "direction", align: "center" },
      { header: "Reference", accessor: "reference" },
      { header: "ID", accessor: "id", cell: (v) => <span className="mono">{v}</span> },
    ],
    []
  );

  const onPreviewRevenue = async () => {
    setRevenuePreviewOn(true);
    await refreshRevenue();
  };

  const onPreviewTransactions = async () => {
    setTxPreviewOn(true);
    await refreshTransactions();
  };

  const revenueMeta = revenueQuery.data ? `${revenueQuery.data.snapshot_id || "—"} • ${revenueQuery.data.generated_at || "—"}` : null;
  const txMeta = transactionsQuery.data ? `${transactionsQuery.data.snapshot_id || "—"} • ${transactionsQuery.data.generated_at || "—"}` : null;

  const revenueCsvRows = useMemo(() => {
    const header = ["period", "revenue"];
    const rows = revenueItems.map((p) => [p.period, p.revenue]);
    return [header, ...rows];
  }, [revenueItems]);

  const txCsvRows = useMemo(() => {
    const header = ["source", "id", "event_date", "created_at", "amount", "currency", "direction", "reference"];
    const rows = txItems.map((t) => [
      t.source,
      t.id,
      t.event_date,
      t.created_at,
      t.amount,
      t.currency,
      t.direction,
      t.reference,
    ]);
    return [header, ...rows];
  }, [txItems]);

  return (
    <div className="u-grid u-gap-4" data-testid="exports">
      <div className="u-grid u-gap-1">
        <h1 className="u-m-0">Exports</h1>
        <div className="u-text-muted">Fetch and download ML exports (JSON/CSV).</div>
      </div>

      <Card title="Filters" subtitle="Applied to both exports">
        <div className="cardGrid">
          <Input label="From date" type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
          <Input label="To date" type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
          <Select
            label="Granularity (revenue series)"
            value={granularity}
            onChange={(e) => setGranularity(e.target.value)}
            options={[
              { label: "Day", value: "day" },
              { label: "Week", value: "week" },
              { label: "Month", value: "month" },
            ]}
          />
          <Input
            label="Transactions limit"
            type="number"
            min={1}
            max={100000}
            value={txLimit}
            onChange={(e) => setTxLimit(e.target.value)}
          />
        </div>
      </Card>

      <div className="cardGrid">
        <Card
          title="Revenue series"
          subtitle={revenueMeta ? `snapshot_id • generated_at: ${revenueMeta}` : "revenue_series export"}
          actions={
            <div className="u-flex u-gap-2">
              <Button size="sm" variant="secondary" onClick={onPreviewRevenue} disabled={revenueQuery.isLoading}>
                Preview
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => downloadJson("revenue_series_export.json", revenueQuery.data)}
                disabled={!revenueQuery.data}
              >
                Download JSON
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => downloadCsv("revenue_series_export.csv", revenueCsvRows)}
                disabled={!revenueQuery.data}
              >
                Download CSV
              </Button>
            </div>
          }
        >
          {granularity === "week" ? (
            <div className="u-text-muted u-mb-2">Week is aggregated client-side from daily export.</div>
          ) : null}
          {!revenuePreviewOn ? (
            <EmptyState compact title="Preview to load" message="Click Preview to fetch revenue series for the selected window." />
          ) : revenueQuery.isLoading ? (
            <Skeleton className="kit-skeletonChart" />
          ) : revenueQuery.isError ? (
            <ErrorState title="Revenue export failed" error={revenueQuery.error} onRetry={() => refreshRevenue()} />
          ) : revenueItems.length === 0 ? (
            <EmptyState title="No revenue points" message="No data for the selected window." />
          ) : (
            <DataTable columns={revenueColumns} data={revenuePreviewRows} />
          )}
        </Card>

        <Card
          title="Transactions"
          subtitle={txMeta ? `snapshot_id • generated_at: ${txMeta}` : "transactions export"}
          actions={
            <div className="u-flex u-gap-2">
              <Button size="sm" variant="secondary" onClick={onPreviewTransactions} disabled={transactionsQuery.isLoading}>
                Preview
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => downloadJson("transactions_export.json", transactionsQuery.data)}
                disabled={!transactionsQuery.data}
              >
                Download JSON
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => downloadCsv("transactions_export.csv", txCsvRows)}
                disabled={!transactionsQuery.data}
              >
                Download CSV
              </Button>
            </div>
          }
        >
          {!txPreviewOn ? (
            <EmptyState compact title="Preview to load" message="Click Preview to fetch transactions for the selected window." />
          ) : transactionsQuery.isLoading ? (
            <Skeleton className="kit-skeletonLg" />
          ) : transactionsQuery.isError ? (
            <ErrorState title="Transactions export failed" error={transactionsQuery.error} onRetry={() => refreshTransactions()} />
          ) : txItems.length === 0 ? (
            <EmptyState title="No transactions" message="No transactions for the selected window." />
          ) : (
            <DataTable columns={txColumns} data={txPreviewRows} />
          )}
          {transactionsQuery.isSuccess && txItems.length > 50 ? (
            <div className="u-text-muted u-mt-2">Preview shows first 50 rows of {txItems.length}.</div>
          ) : null}
        </Card>
      </div>

      {!revenuePreviewOn && !txPreviewOn ? (
        <Card title="Tip">
          <EmptyState compact title="Preview first" message="Use Preview to fetch exports, then download JSON/CSV." />
        </Card>
      ) : null}
    </div>
  );
};

export default Exports;
