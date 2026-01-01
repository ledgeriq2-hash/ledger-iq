import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import reportsApi from "../../api/reportsApi.js";
import Button from "../../components/ui/Button.jsx";
import Card from "../../components/ui/Card.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";
import Input from "../../components/ui/Input.jsx";
import Skeleton from "../../components/ui/Skeleton.jsx";
import StatusPill from "../../components/kit/StatusPill.jsx";
import Table from "../../components/kit/Table.jsx";

const money = (value) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return "?";
  return num.toFixed(2);
};

const Reports = () => {
  const [draftTreasury, setDraftTreasury] = useState({
    from_date: "",
    to_date: "",
    treasury_id: "",
    direction: "",
  });
  const [treasuryFilters, setTreasuryFilters] = useState(draftTreasury);
  const [draftClientId, setDraftClientId] = useState("");
  const [clientId, setClientId] = useState("");

  const treasuryQuery = useQuery({
    queryKey: ["reports", "treasury", treasuryFilters],
    queryFn: () => reportsApi.treasuryReport({
      from_date: treasuryFilters.from_date || undefined,
      to_date: treasuryFilters.to_date || undefined,
      treasury_id: treasuryFilters.treasury_id || undefined,
      direction: treasuryFilters.direction || undefined,
    }),
  });

  const clientStatementQuery = useQuery({
    queryKey: ["reports", "clientStatement", clientId],
    queryFn: () => reportsApi.clientStatement({ client_id: clientId }),
    enabled: Boolean(clientId),
  });

  const treasuryReport = treasuryQuery.data?.data || {};
  const treasuryTotals = treasuryReport?.totals || {};
  const treasuryTransactions = Array.isArray(treasuryReport?.transactions) ? treasuryReport.transactions : [];

  const treasuryRows = useMemo(
    () =>
      treasuryTransactions.map((item, idx) => ({
        key: item.id || `${idx}`,
        created_at: item.created_at,
        treasury_id: item.treasury_id,
        direction: item.direction,
        amount: item.amount,
        reference_type: item.reference_type,
        reference_id: item.reference_id,
      })),
    [treasuryTransactions]
  );

  const statement = clientStatementQuery.data?.data || {};
  const statementLines = Array.isArray(statement?.lines) ? statement.lines : [];

  return (
    <div className="u-grid u-gap-4">
      <h1 className="u-m-0">Reports</h1>

      <Card title="Treasury report" subtitle="Balances and movement history">
        <div className="wizardStepsGrid">
          <Input
            label="From date"
            type="date"
            value={draftTreasury.from_date}
            onChange={(event) => setDraftTreasury((prev) => ({ ...prev, from_date: event.target.value }))}
          />
          <Input
            label="To date"
            type="date"
            value={draftTreasury.to_date}
            onChange={(event) => setDraftTreasury((prev) => ({ ...prev, to_date: event.target.value }))}
          />
          <Input
            label="Treasury ID"
            value={draftTreasury.treasury_id}
            onChange={(event) => setDraftTreasury((prev) => ({ ...prev, treasury_id: event.target.value }))}
            placeholder="Optional UUID"
          />
          <Input
            label="Direction"
            value={draftTreasury.direction}
            onChange={(event) => setDraftTreasury((prev) => ({ ...prev, direction: event.target.value }))}
            placeholder="in/out"
          />
        </div>
        <div className="wizardActionsRow">
          <Button
            variant="ghost"
            type="button"
            onClick={() => {
              const reset = { from_date: "", to_date: "", treasury_id: "", direction: "" };
              setDraftTreasury(reset);
              setTreasuryFilters(reset);
            }}
          >
            Reset
          </Button>
          <Button type="button" onClick={() => setTreasuryFilters(draftTreasury)}>
            Apply
          </Button>
        </div>
      </Card>

      <Card title="Treasury totals">
        {treasuryQuery.isLoading ? (
          <Skeleton className="kit-skeletonLg" />
        ) : treasuryQuery.isError ? (
          <ErrorState compact title="Failed to load treasury report" error={treasuryQuery.error} onRetry={treasuryQuery.refetch} />
        ) : Object.keys(treasuryTotals).length === 0 ? (
          <EmptyState title="No treasury totals yet" message="Record transactions to populate treasury totals." />
        ) : (
          <div className="cardGrid">
            <div>
              <div className="dashboardMeta">In</div>
              <div className="dashboardKpiValue">{money(treasuryTotals.in)}</div>
            </div>
            <div>
              <div className="dashboardMeta">Out</div>
              <div className="dashboardKpiValue">{money(treasuryTotals.out)}</div>
            </div>
            <div>
              <div className="dashboardMeta">Net</div>
              <div className="dashboardKpiValue">{money(treasuryTotals.net)}</div>
            </div>
          </div>
        )}
      </Card>

      <Card title="Treasury movements">
        {treasuryQuery.isLoading ? (
          <Skeleton className="kit-skeletonLg" />
        ) : treasuryQuery.isError ? (
          <ErrorState compact title="Failed to load treasury movements" error={treasuryQuery.error} onRetry={treasuryQuery.refetch} />
        ) : treasuryRows.length === 0 ? (
          <EmptyState title="No movements yet" message="Transactions will appear here once recorded." />
        ) : (
          <Table
            keyField="key"
            columns={[
              { key: "created_at", header: "When" },
              { key: "treasury_id", header: "Treasury" },
              { key: "direction", header: "Dir", render: (row) => <StatusPill tone={row.direction === "in" ? "success" : "warning"}>{row.direction}</StatusPill> },
              { key: "amount", header: "Amount", render: (row) => money(row.amount) },
              { key: "reference_type", header: "Ref Type" },
              { key: "reference_id", header: "Ref ID" },
            ]}
            rows={treasuryRows}
          />
        )}
      </Card>

      <Card title="Client statement" subtitle="Requires a client ID">
        <div className="wizardActionsRow">
          <Input
            label="Client ID"
            value={draftClientId}
            onChange={(event) => setDraftClientId(event.target.value)}
            placeholder="UUID"
          />
          <Button type="button" onClick={() => setClientId(draftClientId.trim())}>
            Load
          </Button>
        </div>
      </Card>

      <Card title="Statement details">
        {!clientId ? (
          <EmptyState title="Client ID required" message="Enter a client ID to load the statement report." />
        ) : clientStatementQuery.isLoading ? (
          <Skeleton className="kit-skeletonLg" />
        ) : clientStatementQuery.isError ? (
          <ErrorState compact title="Failed to load statement" error={clientStatementQuery.error} onRetry={clientStatementQuery.refetch} />
        ) : statementLines.length === 0 ? (
          <EmptyState title="No statement lines" message="The statement did not return any line items." />
        ) : (
          <Table
            keyField="line_id"
            columns={[
              { key: "date", header: "Date" },
              { key: "description", header: "Description" },
              { key: "debit", header: "Debit", render: (row) => money(row.debit) },
              { key: "credit", header: "Credit", render: (row) => money(row.credit) },
              { key: "running_balance", header: "Running", render: (row) => money(row.running_balance) },
              { key: "reference_type", header: "Ref Type" },
              { key: "reference_id", header: "Ref ID" },
            ]}
            rows={statementLines}
          />
        )}
      </Card>
    </div>
  );
};

export default Reports;
