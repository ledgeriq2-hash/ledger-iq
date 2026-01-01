import React, { useEffect, useMemo, useState } from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import billingApi from "../../api/billingApi.js";
import usePermissions from "../../hooks/usePermissions.js";
import useAuth from "../../hooks/useAuth.js";

const UsageBar = ({ label, value = 0, limit }) => {
  const percent = limit ? Math.min(100, Math.round((value / limit) * 100)) : 0;
  return (
    <div style={{ display: "grid", gap: "0.3rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", color: "var(--color-text)", fontWeight: 600 }}>
        <span>{label}</span>
        <span style={{ color: "var(--color-muted)" }}>
          {value} {limit ? `/ ${limit}` : "Unlimited"}
        </span>
      </div>
      <div style={{ background: "var(--color-border)", borderRadius: "999px", overflow: "hidden", height: "10px" }}>
        <div
          style={{
            width: `${percent}%`,
            background: percent > 90 ? "var(--color-primary)" : "var(--color-secondary)",
            height: "100%",
            transition: "width 200ms ease",
          }}
        />
      </div>
    </div>
  );
};

const PlanCard = ({ plan, current, onSelect }) => {
  const isCurrent = current?.code === plan.code;
  return (
    <div
      style={{
        border: isCurrent ? "1px solid var(--color-primary)" : "1px solid var(--color-border)",
        borderRadius: "12px",
        padding: "1rem",
        background: isCurrent
          ? "color-mix(in srgb, var(--color-secondary) 14%, var(--color-surface))"
          : "var(--color-surface)",
        display: "grid",
        gap: "0.4rem",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ margin: 0 }}>{plan.name}</h3>
          <p style={{ margin: 0, color: "var(--color-muted)" }}>{plan.interval === "month" ? "Per month" : plan.interval}</p>
        </div>
        <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--color-text)" }}>
          {plan.price_cents === 0 ? "Free" : `$${(plan.price_cents / 100).toFixed(0)}`}
        </div>
      </div>
      <div style={{ color: "var(--color-text)", fontWeight: 600 }}>Limits</div>
      <div style={{ display: "grid", gap: "0.2rem", color: "var(--color-muted)" }}>
        {Object.entries(plan.limits_json || {}).map(([key, value]) => (
          <div key={key} style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ textTransform: "capitalize" }}>{key.replace("_", " ")}</span>
            <span>{value}</span>
          </div>
        ))}
        {!Object.keys(plan.limits_json || {}).length && <span>No limits</span>}
      </div>
      <button
        onClick={() => onSelect(plan.code)}
        disabled={isCurrent}
        style={{
          marginTop: "0.5rem",
          padding: "0.65rem",
          borderRadius: "8px",
          border: "1px solid var(--color-primary)",
          background: isCurrent ? "var(--color-border)" : "var(--color-primary)",
          color: "var(--color-on-primary)",
          cursor: isCurrent ? "not-allowed" : "pointer",
          fontWeight: 700,
        }}
      >
        {isCurrent ? "Current plan" : "Choose plan"}
      </button>
    </div>
  );
};

const Billing = () => {
  const [status, setStatus] = useState(null);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [actionMessage, setActionMessage] = useState("");
  const { hasRole } = usePermissions();
  const { tenant } = useAuth();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sub, planList] = await Promise.all([billingApi.getSubscription(), billingApi.listPlans()]);
      setStatus(sub);
      setPlans(planList || []);
    } catch (err) {
      setError("Unable to load billing");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const currentPlan = useMemo(() => {
    if (!status?.plan_code) return null;
    return plans.find((p) => p.code === status.plan_code) || status.plan;
  }, [plans, status]);

  const startCheckout = async (planCode) => {
    setActionMessage("Redirecting to checkout...");
    try {
      const result = await billingApi.startCheckout(planCode, window.location.href, window.location.href);
      if (result?.url) {
        window.location.href = result.url;
      } else {
        setActionMessage("Checkout link unavailable");
      }
    } catch (err) {
      setActionMessage("");
      setError(err?.response?.data?.detail || "Unable to start checkout");
    }
  };

  const usage = status?.usage || {};
  const limits = status?.limits || {};

  if (!hasRole("owner") && !hasRole("admin")) {
    return (
      <MainLayout>
        <div style={{ padding: "1rem", color: "var(--color-text)" }}>You need admin or owner access to manage billing.</div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1rem",
        }}
      >
        <div>
          <h2 style={{ margin: 0 }}>Billing</h2>
          <p style={{ margin: 0, color: "var(--color-muted)" }}>{tenant?.name || "Your workspace"}</p>
        </div>
        {loading && <span style={{ color: "var(--color-muted)" }}>Loading...</span>}
      </div>
      {error && (
        <div style={{ marginBottom: "0.75rem", padding: "0.75rem", borderRadius: "8px", background: "color-mix(in srgb, var(--color-primary) 12%, var(--color-surface))", color: "var(--color-text)", border: "1px solid var(--color-primary)" }}>
          {error}
        </div>
      )}
      {actionMessage && (
        <div style={{ marginBottom: "0.75rem", padding: "0.75rem", borderRadius: "8px", background: "color-mix(in srgb, var(--color-secondary) 12%, var(--color-surface))", color: "var(--color-text)", border: "1px solid var(--color-border)" }}>
          {actionMessage}
        </div>
      )}
      <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "1fr 0.9fr" }}>
        <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "12px", padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ color: "var(--color-muted)" }}>Current plan</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--color-text)" }}>
                {currentPlan?.name || status?.plan_code || "Unknown"}
              </div>
              <div style={{ color: "var(--color-muted)" }}>
                Status: {status?.subscription?.status || "inactive"}{" "}
                {status?.subscription?.current_period_end &&
                  `(renews ${new Date(status.subscription.current_period_end).toLocaleDateString()})`}
              </div>
            </div>
            <div style={{ textAlign: "right", color: "var(--color-link)", fontWeight: 700 }}>{tenant?.slug}</div>
          </div>
          <div style={{ marginTop: "1rem", display: "grid", gap: "0.75rem" }}>
            <UsageBar label="Members" value={usage.users} limit={limits.users} />
            <UsageBar label="Invoices" value={usage.invoices} limit={limits.invoices} />
            <UsageBar label="AI calls (this month)" value={usage.ai_calls} limit={limits.ai_calls} />
            <UsageBar label="Storage (MB)" value={usage.storage_mb} limit={limits.storage_mb} />
          </div>
        </div>
        <div style={{ background: "linear-gradient(135deg, var(--color-primary) 0%, color-mix(in srgb, var(--color-primary) 65%, var(--color-secondary)) 100%)", borderRadius: "12px", padding: "1.25rem", color: "var(--color-on-primary)" }}>
          <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>Upgrade or change plan</div>
          <p style={{ marginTop: "0.5rem", color: "var(--color-on-primary)" }}>
            Choose a plan that fits your team. Downgrades take effect at renewal; upgrades activate immediately.
          </p>
          <div style={{ marginTop: "0.75rem", display: "grid", gap: "0.5rem", color: "var(--color-on-primary)" }}>
            <div>✔ Stripe checkout for secure billing</div>
            <div>✔ Usage limits enforced per plan</div>
            <div>✔ View current usage at a glance</div>
          </div>
        </div>
      </div>
      <div style={{ marginTop: "1rem", display: "grid", gap: "1rem", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))" }}>
        {plans.map((plan) => (
          <PlanCard key={plan.code} plan={plan} current={currentPlan} onSelect={startCheckout} />
        ))}
        {!plans.length && (
          <div style={{ padding: "1rem", borderRadius: "10px", border: "1px solid var(--color-border)", background: "var(--color-surface)" }}>
            No plans found. Please contact support.
          </div>
        )}
      </div>
    </MainLayout>
  );
};

export default Billing;
