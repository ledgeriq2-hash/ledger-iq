import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "../../api/generated/index.js";
import { getPortalToken, setPortalToken } from "../../utils/portalTokens.js";
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

const Portal = () => {
  const { token: tokenParam } = useParams();
  const [activeTab, setActiveTab] = useState("summary");
  const [portalToken, setPortalTokenState] = useState(() => tokenParam || getPortalToken());

  useEffect(() => {
    if (tokenParam && tokenParam !== portalToken) {
      setPortalTokenState(tokenParam);
      setPortalToken(tokenParam);
    }
  }, [tokenParam, portalToken]);

  const token = useMemo(() => portalToken || getPortalToken(), [portalToken]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["portal", token],
    queryFn: async () => {
      const [summary, balance, invoices, payments, statement] = await Promise.all([
        api.portal.summary(token),
        api.portal.balance(token),
        api.portal.invoices(token, { page: 1, page_size: 50 }),
        api.portal.payments(token, { page: 1, page_size: 50 }),
        api.portal.statement(token),
      ]);
      return {
        summary,
        balance,
        invoices: invoices?.invoices || [],
        payments: payments?.payments || [],
        statement: statement?.statement || null,
      };
    },
    enabled: Boolean(token),
    retry: 2,
  });

  if (!token) {
    return (
      <div className="portalPage">
        <div className="kit-container portalGrid">
          <Card title="Portal">
            <StatusPill tone="danger">Missing token</StatusPill>
            <div className="u-text-muted">
              This portal link requires a secure access token. Check your invite email or ask an administrator for a valid
              link.
            </div>
          </Card>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="portalPage">
        <div className="kit-container portalGrid">
          <Card title="Portal">
            <Skeleton className="kit-skeleton" />
          </Card>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="portalPage">
        <div className="kit-container portalGrid">
          <Card title="Portal">
            <StatusPill tone="danger">{error.message || "Failed to load portal"}</StatusPill>
          </Card>
        </div>
      </div>
    );
  }

  const client = data?.summary?.client;
  const stats = data?.summary?.stats || {};
  const recent = data?.summary?.recent_activity || [];

  const invoicesColumns = [
    { key: "id", header: "Invoice" },
    { key: "status", header: "Status", render: (row) => <StatusPill tone="info">{row.status}</StatusPill> },
    { key: "total_amount", header: "Total", render: (row) => `${money(row.total_amount)} ${row.currency}` },
  ];

  const paymentsColumns = [
    { key: "id", header: "Payment", render: (row) => row.reference || row.id },
    { key: "method", header: "Method" },
    { key: "amount", header: "Amount", render: (row) => money(row.amount) },
  ];

  return (
    <div className="portalPage">
      <div className="kit-container portalGrid">
        <Card
          title="Portal"
          headerRight={
            <div className="portalTabs">
              <Button type="button" variant={activeTab === "summary" ? "primary" : "ghost"} onClick={() => setActiveTab("summary")}>
                Summary
              </Button>
              <Button type="button" variant={activeTab === "invoices" ? "primary" : "ghost"} onClick={() => setActiveTab("invoices")}>
                Invoices
              </Button>
              <Button type="button" variant={activeTab === "payments" ? "primary" : "ghost"} onClick={() => setActiveTab("payments")}>
                Payments
              </Button>
              <Button type="button" variant={activeTab === "statement" ? "primary" : "ghost"} onClick={() => setActiveTab("statement")}>
                Statement
              </Button>
            </div>
          }
        >
          <div className="portalGrid">
            <div className="kit-card">
              <div className="portalHeader">
                <div>
                  <div className="kit-cardTitle">{client?.name || "Client"}</div>
                  <div>
                    Balance: {money(data?.balance?.balance)} (as of {data?.balance?.as_of_date || "today"})
                  </div>
                  <div>
                    Open invoices: {stats.open_invoices ?? 0} ظت Total open: {money(stats.total_open_amount)}
                  </div>
                </div>
                <StatusPill tone="success">Read-only</StatusPill>
              </div>
            </div>

            {activeTab === "summary" ? (
              <Card title="Recent Activity">
                {recent.length === 0 ? (
                  <StatusPill tone="info">No activity</StatusPill>
                ) : (
                  <Table
                    keyField="timestamp"
                    columns={[
                      { key: "title", header: "Title" },
                      { key: "description", header: "Description" },
                      { key: "timestamp", header: "When" },
                    ]}
                    rows={recent}
                  />
                )}
              </Card>
            ) : null}

            {activeTab === "invoices" ? (
              <Card title="Invoices">
                <Table keyField="id" columns={invoicesColumns} rows={data?.invoices || []} />
              </Card>
            ) : null}

            {activeTab === "payments" ? (
              <Card title="Payments">
                <Table keyField="id" columns={paymentsColumns} rows={data?.payments || []} />
              </Card>
            ) : null}

            {activeTab === "statement" ? (
              <Card title="Statement">
                <pre>{JSON.stringify(data?.statement || {}, null, 2)}</pre>
              </Card>
            ) : null}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Portal;
