import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import Card from "../../components/ui/Card.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";
import LoadingSkeleton from "../../components/ui/LoadingSkeleton.jsx";
import Tag from "../../components/ui/Tag.jsx";
import Button from "../../components/ui/Button.jsx";
import Table from "../../components/kit/Table.jsx";
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

const Treasury = () => {
  const navigate = useNavigate();
  const [selectedTx, setSelectedTx] = useState(null);
  const treasuryQuery = useTreasury();

  const reportRoot = treasuryQuery.data?.data ?? treasuryQuery.data ?? {};
  const totals = reportRoot?.totals ?? reportRoot?.summary ?? {};
  const currency = reportRoot?.currency || "USD";
  const transactions = reportRoot?.transactions ?? reportRoot?.items ?? [];

  const balanceValue = toNumber(totals?.net ?? totals?.balance);

  const rows = useMemo(
    () =>
      (Array.isArray(transactions) ? transactions : []).map((tx) => ({
        id: tx?.id,
        created_at: tx?.created_at,
        description: tx?.description,
        direction: tx?.direction,
        amount: tx?.amount,
        reference_type: tx?.reference_type,
        reference_id: tx?.reference_id,
      })),
    [transactions]
  );

  const handleRowClick = (row) => {
    setSelectedTx(row);
  };

  const closeDrawer = () => setSelectedTx(null);
  const renderSummaryValue = (value) =>
    value === undefined || value === null ? (
      <div className="u-text-muted">Not available</div>
    ) : (
      <div className="dashboardKpiValue">{formatMoney(value, currency)}</div>
    );
  const renderDescriptionButton = (row) => (
    <button
      type="button"
      onClick={() => handleRowClick(row)}
      style={{
        border: "none",
        background: "transparent",
        color: "inherit",
        padding: 0,
        textAlign: "left",
        cursor: "pointer",
      }}
    >
      {row.description || "N/A"}
    </button>
  );

  return (
    <div className="u-grid u-gap-5">
      <div>
        <h1 className="u-m-0">Treasury</h1>
        <p className="u-text-muted u-m-0">
          Treasury is the single source of truth for cash, obligations, and timing.
        </p>
      </div>

      <section className="cardGridBasic">
        <Card
          title="Balance"
          subtitle="Net position across treasury movements"
          actions={
            <Button size="sm" onClick={() => navigate("/reports")}>
              View reports
            </Button>
          }
        >
          {treasuryQuery.isLoading ? (
            <LoadingSkeleton variant="card" rows={2} label="Loading balance" />
          ) : treasuryQuery.isError ? (
            <ErrorState
              compact
              title="Failed to load balance"
              error={treasuryQuery.error}
              onRetry={treasuryQuery.refetch}
            />
          ) : balanceValue === null ? (
            <EmptyState
              compact
              title="No balance yet"
              message="Treasury balance appears after movements are recorded."
            />
          ) : (
            <div className="dashboardKpiValue u-text-primary">
              {formatMoney(balanceValue, currency)}
            </div>
          )}
        </Card>

        <Card title="In / Out / Net" subtitle="Movement summary">
          {treasuryQuery.isLoading ? (
            <LoadingSkeleton variant="card" rows={2} label="Loading summary" />
          ) : treasuryQuery.isError ? (
            <ErrorState
              compact
              title="Failed to load summary"
              error={treasuryQuery.error}
              onRetry={treasuryQuery.refetch}
            />
          ) : (
            <div className="cardGrid">
              <div>
                <div className="dashboardMeta">In</div>
                {renderSummaryValue(totals?.in)}
              </div>
              <div>
                <div className="dashboardMeta">Out</div>
                {renderSummaryValue(totals?.out)}
              </div>
              <div>
                <div className="dashboardMeta">Net</div>
                {renderSummaryValue(totals?.net)}
              </div>
            </div>
          )}
        </Card>
      </section>

      <section className="u-grid u-gap-3">
        <Card title="Transactions" subtitle="Latest treasury activity">
          {treasuryQuery.isLoading ? (
            <LoadingSkeleton variant="table" rows={6} label="Loading transactions" />
          ) : treasuryQuery.isError ? (
            <ErrorState
              compact
              title="Failed to load transactions"
              error={treasuryQuery.error}
              onRetry={treasuryQuery.refetch}
            />
          ) : rows.length === 0 ? (
            <EmptyState
              title="No transactions yet"
              message="Treasury activity will appear here once movements are recorded."
            />
          ) : (
            <Table
              keyField="id"
              columns={[
                {
                  key: "description",
                  header: "Description",
                  render: (row) => renderDescriptionButton(row),
                },
                {
                  key: "direction",
                  header: "Direction",
                  render: (row) => (
                    <Tag tone={row.direction === "in" ? "success" : "warning"}>
                      {row.direction || "N/A"}
                    </Tag>
                  ),
                },
                {
                  key: "amount",
                  header: "Amount",
                  render: (row) => formatMoney(row.amount, currency),
                },
                {
                  key: "created_at",
                  header: "When",
                  render: (row) => formatDateTime(row.created_at),
                },
              ]}
              rows={rows}
            />
          )}
        </Card>
      </section>

      {selectedTx && (
        <div
          role="dialog"
          aria-modal="true"
          onClick={closeDrawer}
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
              maxWidth: "420px",
              height: "100%",
              background: "var(--color-card)",
              boxShadow: "var(--shadow-2)",
              padding: "var(--space-5)",
              overflowY: "auto",
            }}
          >
            <div className="u-flex u-justify-between u-items-center u-gap-3">
              <div>
                <div className="dashboardMeta">Transaction details</div>
                <div className="dashboardKpiValue">
                  {formatMoney(selectedTx.amount, currency)}
                </div>
              </div>
              <Button variant="ghost" onClick={closeDrawer}>
                Close
              </Button>
            </div>
            <div className="u-text-muted u-pad-2">Read-only. No edits.</div>
            <div className="u-grid u-gap-3 u-pad-3">
              <div>
                <div className="dashboardMeta">Direction</div>
                <Tag tone={selectedTx.direction === "in" ? "success" : "warning"}>
                  {selectedTx.direction || "N/A"}
                </Tag>
              </div>
              <div>
                <div className="dashboardMeta">Reference Type</div>
                <div>{selectedTx.reference_type || "N/A"}</div>
              </div>
              <div>
                <div className="dashboardMeta">Reference ID</div>
                <div>{selectedTx.reference_id || "N/A"}</div>
              </div>
              <div>
                <div className="dashboardMeta">Created At</div>
                <div>{formatDateTime(selectedTx.created_at)}</div>
              </div>
              <div>
                <div className="dashboardMeta">Description</div>
                <div>{selectedTx.description || "N/A"}</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Treasury;
