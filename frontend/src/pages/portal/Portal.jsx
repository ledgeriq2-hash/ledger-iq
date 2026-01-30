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
import Banner from "../../components/ui/Banner.jsx";

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
  const [invoiceStatus, setInvoiceStatus] = useState("all");
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [sortOrder, setSortOrder] = useState("newest");

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
      const [summary, balance, payments, statement] = await Promise.all([
        api.portal.summary(token),
        api.portal.balance(token),
        api.portal.payments(token, { page: 1, page_size: 50 }),
        api.portal.statement(token),
      ]);
      return {
        summary,
        balance,
        payments: payments?.payments || [],
        statement: statement?.statement || null,
      };
    },
    enabled: Boolean(token),
    retry: 2,
  });

  useEffect(() => {
    setPage(1);
  }, [invoiceStatus, searchQuery, sortOrder]);

  const invoicesQuery = useQuery({
    queryKey: ["portal", "invoices", token, invoiceStatus, searchQuery, page, pageSize, sortOrder],
    queryFn: async () =>
      api.portal.invoices(token, {
        status: invoiceStatus === "all" ? undefined : invoiceStatus,
        q: searchQuery || undefined,
        page,
        page_size: pageSize,
        sort: sortOrder,
      }),
    enabled: Boolean(token) && activeTab === "invoices",
    retry: 1,
  });

  if (!token) {
    return (
      <div className="portalPage">
        <div className="kit-container portalGrid">
          <Card title="Portal">
            <Banner
              variant="danger"
              title="Missing token"
              message="This portal link requires a secure access token. Check your invite email or ask an administrator for a valid link."
            />
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
            <Banner variant="danger" title="Failed to load portal" message={error.message || "Please try again."} />
          </Card>
        </div>
      </div>
    );
  }

  const client = data?.summary?.client;
  const stats = data?.summary?.stats || {};
  const recent = data?.summary?.recent_activity || [];
  const statement = data?.statement || {};
  const statementLines = Array.isArray(statement?.lines) ? statement.lines : [];

  const invoicesColumns = [
    { key: "id", header: "Invoice" },
    {
      key: "status",
      header: "Status",
      render: (row) => {
        const status = row.status || "UNKNOWN";
        const tone =
          status === "PAID" ? "success" : status === "OVERDUE" ? "danger" : status === "CANCELLED" ? "warning" : "info";
        return <StatusPill tone={tone}>{status}</StatusPill>;
      },
    },
    { key: "total_amount", header: "Total", render: (row) => `${money(row.total_amount)} ${row.currency}` },
    { key: "issue_date", header: "Issued" },
    { key: "due_date", header: "Due", render: (row) => row.due_date || "-" },
  ];

  const paymentsColumns = [
    { key: "id", header: "Payment", render: (row) => row.reference || row.id },
    { key: "method", header: "Method" },
    { key: "amount", header: "Amount", render: (row) => money(row.amount) },
  ];

  const statementColumns = [
    { key: "date", header: "Date" },
    { key: "description", header: "Description" },
    { key: "debit", header: "Debit", render: (row) => money(row.debit) },
    { key: "credit", header: "Credit", render: (row) => money(row.credit) },
    {
      key: "running_balance",
      header: "Running",
      render: (row) => <StatusPill tone="info">{money(row.running_balance)}</StatusPill>,
    },
  ];

  const invoiceRows = invoicesQuery.data?.invoices || [];
  const invoicePage = invoicesQuery.data?.page || page;
  const invoicePages = invoicesQuery.data?.pages || 1;
  const invoiceTotal = invoicesQuery.data?.total || 0;

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
            <div className="kit-card portalHero">
              <div className="portalHeader">
                <div>
                  <div className="kit-cardTitle">{client?.name || "Client"}</div>
                  <div className="kit-muted">Secure, read-only portal access</div>
                </div>
                <StatusPill tone="success">Read-only</StatusPill>
              </div>
              <div className="portalStats">
                <div className="portalStat">
                  <div className="portalStatLabel">Balance</div>
                  <div className="portalStatValue">{money(data?.balance?.balance)}</div>
                  <div className="kit-muted">As of {data?.balance?.as_of_date || "today"}</div>
                </div>
                <div className="portalStat">
                  <div className="portalStatLabel">Open invoices</div>
                  <div className="portalStatValue">{stats.open_invoices ?? 0}</div>
                </div>
                <div className="portalStat">
                  <div className="portalStatLabel">Total open</div>
                  <div className="portalStatValue">{money(stats.total_open_amount)}</div>
                </div>
              </div>
            </div>

            {activeTab === "summary" ? (
              <Card title="Recent Activity">
                {recent.length === 0 ? (
                  <Banner variant="info" message="No activity yet." />
                ) : (
                  <div className="portalTableWrap">
                    <Table
                      keyField="timestamp"
                      columns={[
                        { key: "title", header: "Title" },
                        { key: "description", header: "Description" },
                        { key: "timestamp", header: "When" },
                      ]}
                      rows={recent}
                    />
                  </div>
                )}
              </Card>
            ) : null}

            {activeTab === "invoices" ? (
              <Card title="Invoices">
                <div className="portalGrid" style={{ gap: "0.75rem" }}>
                  <div className="portalTabs">
                    {["all", "open", "paid", "overdue"].map((key) => (
                      <Button
                        key={key}
                        type="button"
                        variant={invoiceStatus === key ? "primary" : "ghost"}
                        onClick={() => setInvoiceStatus(key)}
                      >
                        {key.charAt(0).toUpperCase() + key.slice(1)}
                      </Button>
                    ))}
                  </div>
                  <div className="portalSearch">
                    <input
                      className="kit-input"
                      placeholder="Search invoice number/reference"
                      value={searchInput}
                      onChange={(event) => setSearchInput(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          event.preventDefault();
                          setSearchQuery(searchInput.trim());
                        }
                      }}
                      style={{ minWidth: "240px" }}
                    />
                    <Button type="button" variant="ghost" onClick={() => setSearchQuery(searchInput.trim())}>
                      Search
                    </Button>
                    <select
                      className="kit-select"
                      value={sortOrder}
                      onChange={(event) => setSortOrder(event.target.value)}
                      style={{ minWidth: "160px" }}
                    >
                      <option value="newest">Newest first</option>
                      <option value="oldest">Oldest first</option>
                    </select>
                  </div>

                  {invoicesQuery.isLoading ? (
                    <Skeleton className="kit-skeleton" />
                  ) : invoicesQuery.error ? (
                    <Banner variant="danger" title="Failed to load invoices" message={invoicesQuery.error?.message || "Please try again."} />
                  ) : invoiceRows.length === 0 ? (
                    <Banner variant="info" message="No invoices found." />
                  ) : (
                    <div className="portalTableWrap">
                      <Table keyField="id" columns={invoicesColumns} rows={invoiceRows} />
                    </div>
                  )}

                  <div className="portalPagination">
                    <div className="u-text-muted">
                      {invoiceTotal} total · Page {invoicePage} of {invoicePages}
                    </div>
                    <div className="kit-inline">
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                        disabled={invoicePage <= 1}
                      >
                        Prev
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => setPage((prev) => Math.min(invoicePages, prev + 1))}
                        disabled={invoicePage >= invoicePages}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                </div>
              </Card>
            ) : null}

            {activeTab === "payments" ? (
              <Card title="Payments">
                <div className="portalTableWrap">
                  <Table keyField="id" columns={paymentsColumns} rows={data?.payments || []} />
                </div>
              </Card>
            ) : null}

            {activeTab === "statement" ? (
              <Card
                title="Statement"
                headerRight={
                  <Button type="button" variant="ghost" onClick={() => window.print()}>
                    Print / PDF
                  </Button>
                }
              >
                <div className="portalGrid" style={{ gap: "0.75rem" }}>
                  <div className="portalStats">
                    <div className="portalStat">
                      <div className="portalStatLabel">Opening balance</div>
                      <div className="portalStatValue">{money(statement?.opening_balance)}</div>
                    </div>
                    <div className="portalStat">
                      <div className="portalStatLabel">Closing balance</div>
                      <div className="portalStatValue">{money(statement?.closing_balance)}</div>
                    </div>
                  </div>
                  {statementLines.length === 0 ? (
                    <Banner variant="info" message="No statement activity." />
                  ) : (
                    <div className="portalTableWrap">
                      <Table keyField="line_id" columns={statementColumns} rows={statementLines} />
                    </div>
                  )}
                </div>
              </Card>
            ) : null}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Portal;
