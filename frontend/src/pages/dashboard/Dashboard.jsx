import React from "react";
import { useNavigate } from "react-router-dom";

import Button from "../../components/ui/Button.jsx";
import Card from "../../components/ui/Card.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";
import LoadingSkeleton from "../../components/ui/LoadingSkeleton.jsx";
import Tag from "../../components/ui/Tag.jsx";
import Table from "../../components/kit/Table.jsx";
import { useDashboardMetrics } from "../../hooks/useDashboardMetrics.js";
import { useDashboardRecentTransactions } from "../../hooks/useDashboardRecentTransactions.js";

const formatMoney = (value, currency = "USD") => {
  const number = Number(value);
  if (!Number.isFinite(number)) return "?";
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(number);
};

const formatDateTime = (value) => {
  if (!value) return "?";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
};

const toNumber = (value) => {
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

const Dashboard = () => {
  const navigate = useNavigate();
  const metricsQuery = useDashboardMetrics();
  const recentQuery = useDashboardRecentTransactions();

  const currency = metricsQuery.data?.currency || recentQuery.data?.currency || "USD";
  const kpis = metricsQuery.data?.kpis;
  const netCash = toNumber(kpis?.net_cash);
  const recentTransactions = Array.isArray(recentQuery.data?.items) ? recentQuery.data.items : [];

  const goTo = (path) => () => navigate(path);
  const kpiEmptyAction = {
    actionLabel: "View reports",
    onAction: goTo("/reports"),
  };

  const kpiTiles = [
    {
      key: "revenue",
      title: "Revenue",
      subtitle: "Last 12 months",
      value: kpis?.revenue,
      emptyTitle: "No revenue yet",
      emptyMessage: "Post invoices to start tracking revenue.",
    },
    {
      key: "expenses",
      title: "Expenses",
      subtitle: "Last 12 months",
      value: kpis?.expenses,
      emptyTitle: "No expenses yet",
      emptyMessage: "Expense totals appear once costs are recorded.",
    },
    {
      key: "profit",
      title: "Profit",
      subtitle: "Revenue minus expenses",
      value: kpis?.profit,
      emptyTitle: "No profit yet",
      emptyMessage: "Profit is available after revenue and expenses post.",
    },
    {
      key: "net_cash",
      title: "Net Cash",
      subtitle: "Treasury snapshot",
      value: kpis?.net_cash,
      emptyTitle: "No net cash yet",
      emptyMessage: "Net cash updates when treasury movements post.",
    },
  ];

  const renderKpiValue = (value, emptyTitle, emptyMessage) => {
    if (metricsQuery.isLoading) {
      return <LoadingSkeleton variant="card" rows={1} label="Loading KPI" />;
    }
    if (metricsQuery.isError) {
      return (
        <ErrorState
          compact
          title="Failed to load KPI"
          error={metricsQuery.error}
          onRetry={metricsQuery.refetch}
        />
      );
    }
    const numeric = toNumber(value);
    if (numeric === null) {
      return (
        <EmptyState
          compact
          title={emptyTitle}
          message={emptyMessage}
          actionLabel={kpiEmptyAction.actionLabel}
          onAction={kpiEmptyAction.onAction}
        />
      );
    }
    return <div className="dashboardKpiValue">{formatMoney(numeric, currency)}</div>;
  };

  return (
    <div className="u-grid u-gap-5" data-testid="dashboard-root">
      <section className="u-grid u-gap-3">
        <div className="u-flex u-justify-between u-items-center u-gap-3">
          <h2 className="u-m-0">KPIs</h2>
          <div className="dashboardMeta">Updated: {metricsQuery.data?.last_updated || "N/A"}</div>
        </div>
        <div className="cardGrid">
          {kpiTiles.map((tile) => (
            <Card key={tile.key} title={tile.title} subtitle={tile.subtitle}>
              {renderKpiValue(tile.value, tile.emptyTitle, tile.emptyMessage)}
            </Card>
          ))}
        </div>
      </section>

      <section className="cardGridBasic">
        <Card title="Treasury snapshot" subtitle="Balance and flow summary">
          {metricsQuery.isLoading ? (
            <LoadingSkeleton variant="card" rows={2} label="Loading treasury snapshot" />
          ) : metricsQuery.isError ? (
            <ErrorState
              compact
              title="Failed to load treasury snapshot"
              error={metricsQuery.error}
              onRetry={metricsQuery.refetch}
            />
          ) : netCash === null ? (
            <EmptyState
              title="No treasury snapshot yet"
              message="Net cash appears after treasury movements are recorded."
              actionLabel="View treasury"
              onAction={goTo("/treasury")}
            />
          ) : (
            <div className="u-grid u-gap-3">
              <div>
                <div className="dashboardMeta">Balance</div>
                <div className="dashboardKpiValue">{formatMoney(netCash, currency)}</div>
              </div>
              <div className="u-text-muted">
                In/Out summary is not available in dashboard metrics.
              </div>
            </div>
          )}
        </Card>

        <Card title="Quick actions" subtitle="Guided navigation">
          <div className="u-flex u-wrap u-gap-2">
            <Button onClick={goTo("/payments")}>Record payment</Button>
            <Button onClick={goTo("/invoices")}>Create invoice</Button>
            <Button onClick={goTo("/treasury")}>View treasury</Button>
          </div>
        </Card>
      </section>

      <section className="u-grid u-gap-3">
        <Card
          title="AI alerts"
          subtitle="Advisory insights only"
          actions={<Tag>AI Insight - Advisory Only</Tag>}
        >
          <EmptyState
            title="AI insights are advisory only"
            message="Dashboard stays read-only. Visit AI to review insights and explanations."
            actionLabel="View AI insights"
            onAction={goTo("/ai")}
          />
        </Card>
      </section>

      <section className="u-grid u-gap-3">
        <Card
          title="Recent activity"
          subtitle="Recent transactions"
          actions={
            <Button size="sm" onClick={goTo("/treasury")}>
              View all
            </Button>
          }
        >
          {recentQuery.isLoading ? (
            <LoadingSkeleton variant="table" rows={5} label="Loading recent activity" />
          ) : recentQuery.isError ? (
            <ErrorState
              compact
              title="Failed to load recent activity"
              error={recentQuery.error}
              onRetry={recentQuery.refetch}
            />
          ) : recentTransactions.length === 0 ? (
            <EmptyState
              title="No recent activity"
              message="Transactions will appear here once they are recorded."
              actionLabel="View treasury"
              onAction={goTo("/treasury")}
            />
          ) : (
            <Table
              keyField="id"
              columns={[
                { key: "description", header: "Description" },
                { key: "reference_type", header: "Type", render: (row) => row.reference_type || "N/A" },
                {
                  key: "direction",
                  header: "Direction",
                  render: (row) => (
                    <Tag tone={row.direction === "in" ? "success" : "warning"}>{row.direction}</Tag>
                  ),
                },
                {
                  key: "amount",
                  header: "Amount",
                  render: (row) => formatMoney(row.amount, recentQuery.data?.currency || currency),
                },
                { key: "created_at", header: "When", render: (row) => formatDateTime(row.created_at) },
              ]}
              rows={recentTransactions}
            />
          )}
        </Card>
      </section>
    </div>
  );
};

export default Dashboard;
