import React, { useEffect, useMemo, useState } from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import billingApi from "../../api/billingApi.js";
import usePermissions from "../../hooks/usePermissions.js";
import useAuth from "../../hooks/useAuth.js";

const UsageBar = ({ label, value = 0, limit }) => {
  const percent = limit ? Math.min(100, Math.round((value / limit) * 100)) : 0;
  return (
    <div style={{ display: "grid", gap: "0.3rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", color: "#0f172a", fontWeight: 600 }}>
        <span>{label}</span>
        <span style={{ color: "#475569" }}>
          {value} {limit ? `/ ${limit}` : "Unlimited"}
        </span>
      </div>
      <div style={{ background: "#e2e8f0", borderRadius: "999px", overflow: "hidden", height: "10px" }}>
        <div
          style={{
            width: `${percent}%`,
            background: percent > 90 ? "#ef4444" : "#0ea5e9",
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
        border: `1px solid ${isCurrent ? "#0ea5e9" : "#e2e8f0"}`,
        borderRadius: "12px",
        padding: "1rem",
        background: isCurrent ? "#f0f9ff" : "#fff",
        display: "grid",
        gap: "0.4rem",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ margin: 0 }}>{plan.name}</h3>
          <p style={{ margin: 0, color: "#475569" }}>{plan.interval === "month" ? "Per month" : plan.interval}</p>
        </div>
        <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#0f172a" }}>
          {plan.price_cents === 0 ? "Free" : `$${(plan.price_cents / 100).toFixed(0)}`}
        </div>
      </div>
      <div style={{ color: "#0f172a", fontWeight: 600 }}>Limits</div>
      <div style={{ display: "grid", gap: "0.2rem", color: "#475569" }}>
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
          border: "1px solid #0ea5e9",
          background: isCurrent ? "#cbd5e1" : "#0ea5e9",
          color: "#fff",
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
        <div style={{ padding: "1rem", color: "#0f172a" }}>You need admin or owner access to manage billing.</div>
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
          <p style={{ margin: 0, color: "#475569" }}>{tenant?.name || "Your workspace"}</p>
        </div>
        {loading && <span style={{ color: "#475569" }}>Loading...</span>}
      </div>
      {error && (
        <div style={{ marginBottom: "0.75rem", padding: "0.75rem", borderRadius: "8px", background: "#fef2f2", color: "#b91c1c" }}>
          {error}
        </div>
      )}
      {actionMessage && (
        <div style={{ marginBottom: "0.75rem", padding: "0.75rem", borderRadius: "8px", background: "#ecfeff", color: "#0f172a" }}>
          {actionMessage}
        </div>
      )}
      <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "1fr 0.9fr" }}>
        <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: "12px", padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ color: "#475569" }}>Current plan</div>
              <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#0f172a" }}>
                {currentPlan?.name || status?.plan_code || "Unknown"}
              </div>
              <div style={{ color: "#475569" }}>
                Status: {status?.subscription?.status || "inactive"}{" "}
                {status?.subscription?.current_period_end &&
                  `(renews ${new Date(status.subscription.current_period_end).toLocaleDateString()})`}
              </div>
            </div>
            <div style={{ textAlign: "right", color: "#0ea5e9", fontWeight: 700 }}>{tenant?.slug}</div>
          </div>
          <div style={{ marginTop: "1rem", display: "grid", gap: "0.75rem" }}>
            <UsageBar label="Members" value={usage.users} limit={limits.users} />
            <UsageBar label="Invoices" value={usage.invoices} limit={limits.invoices} />
            <UsageBar label="AI calls (this month)" value={usage.ai_calls} limit={limits.ai_calls} />
            <UsageBar label="Storage (MB)" value={usage.storage_mb} limit={limits.storage_mb} />
          </div>
        </div>
        <div style={{ background: "linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%)", borderRadius: "12px", padding: "1.25rem", color: "#fff" }}>
          <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>Upgrade or change plan</div>
          <p style={{ marginTop: "0.5rem", color: "#e0f2fe" }}>
            Choose a plan that fits your team. Downgrades take effect at renewal; upgrades activate immediately.
          </p>
          <div style={{ marginTop: "0.75rem", display: "grid", gap: "0.5rem", color: "#e0f2fe" }}>
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
          <div style={{ padding: "1rem", borderRadius: "10px", border: "1px solid #e2e8f0", background: "#fff" }}>
            No plans found. Please contact support.
          </div>
        )}
      </div>
    </MainLayout>
  );
};

export default Billing;
