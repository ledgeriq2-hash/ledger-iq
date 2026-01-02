import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import Card from "../../components/ui/Card.jsx";
import Button from "../../components/ui/Button.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import Skeleton from "../../components/ui/Skeleton.jsx";
import { api } from "../../api/generated/index.js";

const DataAssessment = () => {
  const revenueExportQuery = useQuery({
    queryKey: ["ml", "exports", "revenue_series", { granularity: "month" }],
    queryFn: () => api.ml.exportRevenueSeries({ granularity: "month", limit: 20_000 }),
    staleTime: 30_000,
  });

  const txExportQuery = useQuery({
    queryKey: ["ml", "exports", "transactions"],
    queryFn: () => api.ml.exportTransactions({ limit: 10_000 }),
    staleTime: 30_000,
  });

  const revenueItems = revenueExportQuery.data?.items || [];
  const hasRevenueHistory = Array.isArray(revenueItems) && revenueItems.some((p) => Number(p?.revenue || 0) > 0);

  const txCount = Array.isArray(txExportQuery.data?.items) ? txExportQuery.data.items.length : null;

  const readiness = useMemo(() => {
    const revenueStatus = hasRevenueHistory ? "Ready" : "Missing";
    const transactionsStatus = typeof txCount === "number" && txCount > 0 ? "Ready" : "Missing";
    const overall = revenueStatus === "Ready" && transactionsStatus === "Ready" ? "Ready" : "Incomplete";
    return { overall, revenueStatus, transactionsStatus };
  }, [hasRevenueHistory, txCount]);

  const formatGeneratedAt = (value) => {
    if (!value) return "—";
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return String(value);
    return dt.toLocaleString();
  };

  const downloadJson = (filename, data) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="u-grid u-gap-4" data-testid="data-assessment">
      <div className="u-grid u-gap-1">
        <h1 className="u-m-0">Data Assessment</h1>
        <div className="u-text-muted">Basic data readiness checks (no AI logic).</div>
      </div>

      <div className="cardGrid">
        <Card title="Overall">
          {revenueExportQuery.isLoading || txExportQuery.isLoading ? (
            <Skeleton className="kit-skeletonLg" />
          ) : revenueExportQuery.isError || txExportQuery.isError ? (
            <div className="formError">Failed to evaluate readiness.</div>
          ) : (
            <div className="dashboardKpiValue">{readiness.overall}</div>
          )}
        </Card>
        <Card title="Revenue history">
          {revenueExportQuery.isLoading ? (
            <Skeleton className="kit-skeletonLg" />
          ) : revenueExportQuery.isError ? (
            <div className="formError">Failed to load revenue series.</div>
          ) : (
            <div className="dashboardKpiValue">{readiness.revenueStatus}</div>
          )}
        </Card>
        <Card title="Transactions">
          {txExportQuery.isLoading ? (
            <Skeleton className="kit-skeletonLg" />
          ) : txExportQuery.isError ? (
            <div className="formError">Failed to load transactions.</div>
          ) : (
            <div className="dashboardKpiValue">{readiness.transactionsStatus}</div>
          )}
        </Card>
        <Card title="Transaction count">
          {txExportQuery.isLoading ? (
            <Skeleton className="kit-skeletonLg" />
          ) : txExportQuery.isError ? (
            <div className="formError">—</div>
          ) : (
            <div className="dashboardKpiValue">{typeof txCount === "number" ? txCount : "—"}</div>
          )}
        </Card>
      </div>

      <Card title="What this checks" subtitle="Current scope">
        <ul className="marketingBullets">
          <li>Presence of revenue history in ML exports</li>
          <li>Presence of at least one transaction in ML exports</li>
          <li>Displays readiness without running AI</li>
        </ul>
        <div className="u-grid u-gap-3">
          <div className="u-grid u-gap-1">
            <div className="u-text-muted">Revenue series export</div>
            {revenueExportQuery.isLoading ? (
              <Skeleton className="kit-skeletonMd" />
            ) : revenueExportQuery.isError ? (
              <div className="formError">Failed to load revenue export.</div>
            ) : (
              <div className="u-grid u-gap-1">
                <div>
                  <span className="u-text-muted">snapshot_id:</span> {revenueExportQuery.data?.snapshot_id || "—"}
                </div>
                <div>
                  <span className="u-text-muted">generated_at:</span>{" "}
                  {formatGeneratedAt(revenueExportQuery.data?.generated_at)}
                </div>
                <div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => downloadJson("revenue_series_export.json", revenueExportQuery.data)}
                    disabled={!revenueExportQuery.data}
                  >
                    Download JSON
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="u-grid u-gap-1">
            <div className="u-text-muted">Transactions export</div>
            {txExportQuery.isLoading ? (
              <Skeleton className="kit-skeletonMd" />
            ) : txExportQuery.isError ? (
              <div className="formError">Failed to load transactions export.</div>
            ) : (
              <div className="u-grid u-gap-1">
                <div>
                  <span className="u-text-muted">snapshot_id:</span> {txExportQuery.data?.snapshot_id || "—"}
                </div>
                <div>
                  <span className="u-text-muted">generated_at:</span> {formatGeneratedAt(txExportQuery.data?.generated_at)}
                </div>
                <div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => downloadJson("transactions_export.json", txExportQuery.data)}
                    disabled={!txExportQuery.data}
                  >
                    Download JSON
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>

      {revenueExportQuery.isSuccess && txExportQuery.isSuccess && readiness.overall !== "Ready" ? (
        <Card title="Next steps">
          <EmptyState
            title="Add baseline financial data"
            message="Record treasury transactions (in/out) to populate KPIs and enable forecasting."
          />
        </Card>
      ) : null}
    </div>
  );
};

export default DataAssessment;
