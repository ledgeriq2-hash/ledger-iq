import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import adminApi from "../../api/adminApi.js";
import usePermissions from "../../hooks/usePermissions.js";

const MiniChart = ({ usage }) => {
  const maxVal = usage.reduce((acc, row) => Math.max(acc, row.invoices_created + row.payments_created), 0) || 1;
  return (
    <div style={{ display: "flex", gap: "0.4rem", alignItems: "flex-end", minHeight: "120px" }}>
      {usage.map((row) => {
        const height = ((row.invoices_created + row.payments_created) / maxVal) * 100;
        return (
          <div key={row.date} style={{ flex: 1, textAlign: "center" }}>
            <div
              style={{
                height: `${Math.max(height, 6)}px`,
                background: "var(--color-primary)",
                borderRadius: "6px 6px 0 0",
              }}
              title={`${row.date}: ${row.invoices_created + row.payments_created} activity`}
            />
            <div style={{ fontSize: "0.7rem", color: "var(--color-muted)", marginTop: "0.25rem" }}>
              {new Date(row.date).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const TenantOverview = () => {
  const { id } = useParams();
  const { hasRole } = usePermissions();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await adminApi.tenantOverview(id);
        setData(response);
      } catch (err) {
        setError("Failed to load tenant overview");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  if (!hasRole("owner") && !hasRole("admin")) {
    return <div className="u-pad-4">You need admin or owner permissions to view this page.</div>;
  }

  return (
    <div className="u-pad-4">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2 style={{ margin: 0 }}>Tenant Overview</h2>
        {loading && <span style={{ color: "var(--color-muted)" }}>Loading...</span>}
      </div>
      {error && <div style={{ color: "var(--color-primary)", marginBottom: "0.75rem" }}>{error}</div>}
      {data && (
        <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "1.3fr 0.7fr" }}>
          <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "10px", padding: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 style={{ margin: 0 }}>{data.tenant.name}</h3>
                <p style={{ margin: 0, color: "var(--color-muted)" }}>{data.tenant.slug}</p>
              </div>
              {data.tenant.is_soft_launch && (
                <span
                  style={{
                    padding: "0.3rem 0.6rem",
                    background: "color-mix(in srgb, var(--color-secondary) 35%, transparent)",
                    borderRadius: "6px",
                    border: "1px solid var(--color-secondary)",
                    color: "var(--color-text)",
                    fontSize: "0.85rem",
                  }}
                >
                  Soft launch
                </span>
              )}
            </div>
            <div style={{ marginTop: "0.75rem", display: "grid", gap: "0.6rem" }}>
              <div>Owner: {data.tenant.owner_email || "Unknown"}</div>
              <div>Created: {new Date(data.tenant.created_at).toLocaleString()}</div>
              <div>Last login: {data.last_login_at ? new Date(data.last_login_at).toLocaleString() : "—"}</div>
              <div>
                Totals: {data.totals?.invoices || 0} invoices • {data.totals?.payments || 0} payments
              </div>
            </div>
            <div style={{ marginTop: "1rem" }}>
              <h4 style={{ margin: "0 0 0.5rem" }}>Usage (last 30 days)</h4>
              <MiniChart usage={data.usage || []} />
            </div>
          </div>

          <div style={{ display: "grid", gap: "1rem" }}>
            <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "10px", padding: "1rem" }}>
              <h4 style={{ marginTop: 0 }}>Recent Errors</h4>
              <div style={{ maxHeight: "180px", overflow: "auto" }}>
                {(data.errors || []).map((e) => (
                  <div key={e.id} style={{ padding: "0.4rem 0", borderBottom: "1px solid var(--color-border)" }}>
                    <div style={{ fontWeight: 600 }}>{e.status_code}</div>
                    <div style={{ color: "var(--color-muted)", fontSize: "0.9rem" }}>
                      {e.method} {e.path}
                    </div>
                    <div style={{ color: "var(--color-primary)", fontSize: "0.9rem" }}>{e.error_message}</div>
                  </div>
                ))}
                {!(data.errors || []).length && <div>No recent errors</div>}
              </div>
            </div>
            <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "10px", padding: "1rem" }}>
              <h4 style={{ marginTop: 0 }}>Recent Feedback</h4>
              <div style={{ maxHeight: "180px", overflow: "auto" }}>
                {(data.feedback || []).map((f) => (
                  <div key={f.id} style={{ padding: "0.4rem 0", borderBottom: "1px solid var(--color-border)" }}>
                    <div style={{ fontWeight: 600, textTransform: "capitalize" }}>{f.category}</div>
                    <div style={{ color: "var(--color-text)" }}>{f.message}</div>
                    <div style={{ color: "var(--color-muted)", fontSize: "0.85rem" }}>
                      {new Date(f.created_at).toLocaleString()}
                    </div>
                  </div>
                ))}
                {!(data.feedback || []).length && <div>No feedback yet</div>}
              </div>
            </div>
            <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "10px", padding: "1rem" }}>
              <h4 style={{ marginTop: 0 }}>Billing</h4>
              <div style={{ display: "grid", gap: "0.4rem", color: "var(--color-text)" }}>
                <div>Plan: {data.billing?.plan?.name || data.billing?.plan_code || "Unknown"}</div>
                <div>Status: {data.billing?.subscription?.status || "inactive"}</div>
                <div>
                  Renew:{' '}
                  {data.billing?.subscription?.current_period_end
                    ? new Date(data.billing.subscription.current_period_end).toLocaleDateString()
                    : "—"}
                </div>
                <div style={{ marginTop: "0.5rem", display: "grid", gap: "0.25rem", color: "var(--color-muted)" }}>
                  <div>Members: {data.billing?.usage?.users ?? 0}</div>
                  <div>Invoices: {data.billing?.usage?.invoices ?? 0}</div>
                  <div>AI calls: {data.billing?.usage?.ai_calls ?? 0}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TenantOverview;
