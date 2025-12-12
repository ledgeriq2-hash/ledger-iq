import React, { useEffect, useMemo, useState } from "react";
import axiosClient from "../../api/axiosClient";

const formatCurrency = (value, currency = "usd") => {
  if (value === null || value === undefined) return "N/A";
  const amount = Number(value);
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency: (currency || "USD").toUpperCase(),
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(amount);
};

const ProgressBar = ({ value = 0, limit, warn = false }) => {
  const percentage = limit ? Math.min((value / limit) * 100, 100) : 0;
  const bg = warn ? "#f97316" : "#22c55e";
  return (
    <div style={{ background: "#e2e8f0", borderRadius: "999px", height: "10px", overflow: "hidden" }}>
      <div
        style={{
          width: `${percentage}%`,
          background: bg,
          height: "100%",
          transition: "width 0.25s ease",
        }}
      />
    </div>
  );
};

const BillingOverview = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axiosClient.get("/billing/overview");
      setData(res.data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const usageRows = useMemo(() => {
    const usage = data?.usage || {};
    const limits = data?.limits || {};
    return [
      {
        key: "invoices_this_month",
        label: "Invoices this month",
        value: usage.invoices_this_month ?? 0,
        limit: limits.max_invoices_per_month,
      },
      {
        key: "ai_calls_this_month",
        label: "AI calls this month",
        value: usage.ai_calls_this_month ?? 0,
        limit: limits.max_ai_calls_per_month,
      },
      {
        key: "storage_usage_mb",
        label: "Storage (MB)",
        value: usage.storage_usage_mb ?? 0,
        limit: limits.max_storage_mb,
      },
    ];
  }, [data]);

  const warnings = usageRows.filter(
    (row) => row.limit && row.limit > 0 && row.value / row.limit >= 0.8
  );

  if (loading) {
    return (
      <div style={styles.centered}>
        <div style={styles.spinner} aria-hidden />
        <p style={{ margin: 0, fontWeight: 600 }}>Loading billing...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ ...styles.card, border: "1px solid #fecdd3", background: "#fff1f2", color: "#9f1239" }}>
        <p style={{ margin: 0, fontWeight: 700 }}>Failed to load billing overview.</p>
        <p style={{ margin: "0.25rem 0 0 0" }}>{error?.message || "Please try again."}</p>
        <button style={styles.buttonGhost} onClick={load}>
          Retry
        </button>
      </div>
    );
  }

  const plan = data?.plan || {};
  const manageUrl = data?.stripe_customer_portal_url || data?.checkout_url || null;

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem", alignItems: "center" }}>
        <div>
          <h1 style={{ margin: 0 }}>Billing overview</h1>
          <p style={{ margin: "0.25rem 0 0 0", color: "#475569" }}>
            Current plan and usage vs limits.
          </p>
        </div>
        {manageUrl && (
          <a href={manageUrl} style={styles.buttonPrimary}>
            Manage subscription
          </a>
        )}
      </div>

      <div style={styles.card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "1rem" }}>
          <div>
            <p style={styles.label}>Current plan</p>
            <h2 style={{ margin: "0.15rem 0" }}>{plan.plan_name || "Unknown plan"}</h2>
            <p style={{ margin: 0, color: "#475569" }}>
              {plan.price !== null && plan.price !== undefined
                ? `${formatCurrency(plan.price, plan.currency)} / ${plan.billing_period || "period"}`
                : "Price not available"}
            </p>
          </div>
          {plan.plan_code && (
            <span style={styles.pill}>{plan.plan_code}</span>
          )}
        </div>
      </div>

      <div style={styles.card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0 }}>Usage</h3>
          {warnings.length > 0 && (
            <span style={styles.warningPill}>Approaching limit</span>
          )}
        </div>
        <div style={{ display: "grid", gap: "1rem", marginTop: "1rem" }}>
          {usageRows.map((row) => {
            const warn = row.limit && row.limit > 0 && row.value / row.limit >= 0.8;
            return (
              <div key={row.key} style={{ display: "grid", gap: "0.35rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ color: "#0f172a", fontWeight: 600 }}>{row.label}</span>
                  <span style={{ color: warn ? "#c2410c" : "#475569", fontWeight: 600 }}>
                    {row.value}
                    {row.limit ? ` / ${row.limit}` : " • Unlimited"}
                  </span>
                </div>
                <ProgressBar value={row.value} limit={row.limit} warn={warn} />
                {warn && (
                  <span style={{ color: "#c2410c", fontSize: "0.9rem" }}>
                    You’ve used {Math.round((row.value / row.limit) * 100)}% of your limit.
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

const styles = {
  card: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: "14px",
    padding: "1.25rem",
    boxShadow: "0 4px 12px rgba(15, 23, 42, 0.04)",
  },
  pill: {
    borderRadius: "999px",
    background: "#eef2ff",
    color: "#4338ca",
    padding: "0.35rem 0.75rem",
    fontWeight: 700,
    fontSize: "0.9rem",
    border: "1px solid #c7d2fe",
  },
  warningPill: {
    borderRadius: "999px",
    background: "#fff7ed",
    color: "#c2410c",
    padding: "0.3rem 0.7rem",
    fontWeight: 700,
    border: "1px solid #fed7aa",
  },
  label: { margin: 0, textTransform: "uppercase", fontSize: "0.75rem", letterSpacing: "0.06em", color: "#94a3b8" },
  buttonPrimary: {
    background: "#6366f1",
    color: "#fff",
    padding: "0.65rem 1rem",
    borderRadius: "10px",
    border: "1px solid #4f46e5",
    textDecoration: "none",
    fontWeight: 700,
  },
  buttonGhost: {
    marginTop: "0.75rem",
    background: "#fff",
    color: "#be123c",
    padding: "0.55rem 0.9rem",
    borderRadius: "10px",
    border: "1px solid #fda4af",
    cursor: "pointer",
    fontWeight: 600,
  },
  centered: {
    padding: "1.5rem",
    display: "grid",
    gap: "0.75rem",
    justifyItems: "center",
    color: "#0f172a",
  },
  spinner: {
    width: "32px",
    height: "32px",
    border: "4px solid #e2e8f0",
    borderTopColor: "#6366f1",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
};

export default BillingOverview;
