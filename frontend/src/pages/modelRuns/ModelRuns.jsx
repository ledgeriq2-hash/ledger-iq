import React, { useMemo } from "react";

import Card from "../../components/ui/Card.jsx";
import DataTable from "../../components/ui/DataTable.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";
import Button from "../../components/ui/Button.jsx";
import { useAiRuns } from "../../hooks/useAiRuns.js";

const formatDateTime = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return String(iso);
  }
};

const ModelRuns = () => {
  const runsQuery = useAiRuns();
  const refreshRuns = runsQuery.refetch;

  const rows = runsQuery.data?.items || [];

  const columns = useMemo(
    () => [
      { header: "Status", accessor: "status" },
      { header: "Started", accessor: "started_at", cell: (v) => formatDateTime(v) },
      { header: "Finished", accessor: "finished_at", cell: (v) => formatDateTime(v) },
      { header: "Run ID", accessor: "id", cell: (v) => <span className="mono">{v}</span> },
      { header: "Error", accessor: "error", cell: (v) => (v ? <span className="u-text-muted">{String(v)}</span> : "—") },
    ],
    []
  );

  return (
    <div className="u-grid u-gap-4" data-testid="model-runs">
      <div className="u-flex u-justify-between u-items-center u-wrap u-gap-3">
        <div className="u-grid u-gap-1">
          <h1 className="u-m-0">Model Runs</h1>
          <div className="u-text-muted">Heuristic AI runs stored in `ai_runs`.</div>
        </div>
        <Button variant="secondary" onClick={() => refreshRuns()} disabled={runsQuery.isFetching}>
          Refresh
        </Button>
      </div>

      <Card title="Runs">
        {runsQuery.isLoading ? (
          <DataTable columns={columns} data={[]} loading />
        ) : runsQuery.isError ? (
          <ErrorState title="Couldn't load model runs" error={runsQuery.error} onRetry={() => refreshRuns()} />
        ) : rows.length === 0 ? (
          <EmptyState title="No runs yet" message="Run AI to generate insights and runs." />
        ) : (
          <DataTable columns={columns} data={rows} />
        )}
      </Card>
    </div>
  );
};

export default ModelRuns;
