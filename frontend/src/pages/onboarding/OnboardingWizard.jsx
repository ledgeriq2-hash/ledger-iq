import React, { useEffect, useMemo, useState } from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import Card from "../../components/ui/Card.jsx";
import Input from "../../components/ui/Input.jsx";
import Button from "../../components/ui/Button.jsx";
import onboardingApi from "../../api/onboardingApi.js";
import useNotifications from "../../hooks/useNotifications.js";
import useAuth from "../../hooks/useAuth.js";

const StepBadge = ({ label, active, done }) => (
  <div
    style={{
      display: "flex",
      alignItems: "center",
      gap: "0.5rem",
      color: active ? "#0f172a" : "#475569",
      fontWeight: active ? 700 : 600,
    }}
  >
    <span
      style={{
        width: "24px",
        height: "24px",
        borderRadius: "999px",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        background: done ? "#22c55e" : active ? "#0ea5e9" : "#e2e8f0",
        color: done || active ? "#fff" : "#475569",
        fontSize: "0.85rem",
      }}
    >
      {done ? "✓" : label[0]}
    </span>
    {label}
  </div>
);

const OnboardingWizard = () => {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);
  const [form, setForm] = useState({
    logo_url: "",
    currency: "USD",
    fiscal_year_start: "01-01",
    chart_preset: "basic",
  });
  const { addNotification } = useNotifications();
  const { tenant } = useAuth();

  const load = async () => {
    setLoading(true);
    try {
      const data = await onboardingApi.getStatus();
      setStatus(data);
      setForm((prev) => ({
        ...prev,
        logo_url: data.logo_url || "",
        currency: data.currency || prev.currency,
        fiscal_year_start: data.fiscal_year_start || prev.fiscal_year_start,
        chart_preset: data.chart_preset || prev.chart_preset,
      }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const currentStep = useMemo(() => status?.step || "profile", [status]);

  const saveProfile = async () => {
    setLoading(true);
    const payload = { ...form, profile_completed: true, step: "sample" };
    const data = await onboardingApi.updateStatus(payload);
    setStatus(data);
    setLoading(false);
    addNotification({ title: "Saved", message: "Workspace profile updated" });
  };

  const loadSampleData = async () => {
    setLoading(true);
    const data = await onboardingApi.createSampleData();
    setStatus(data);
    setLoading(false);
    addNotification({ title: "Sample data", message: "Demo customers and invoices added" });
  };

  const skipSample = async () => {
    setLoading(true);
    const data = await onboardingApi.updateStatus({ step: "done" });
    setStatus(data);
    setLoading(false);
  };

  const markDone = async () => {
    setLoading(true);
    const data = await onboardingApi.updateStatus({ step: "done" });
    setStatus(data);
    setLoading(false);
    addNotification({ title: "Onboarding", message: "You're all set!" });
  };

  const disabled = loading;

  return (
    <MainLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div>
          <h2 style={{ margin: 0 }}>Welcome, {tenant?.name || "team"}</h2>
          <p style={{ margin: 0, color: "#475569" }}>Guide your workspace setup in three quick steps.</p>
        </div>
        {loading && <span style={{ color: "#475569" }}>Saving...</span>}
      </div>

      <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "1fr 0.45fr" }}>
        <Card title="Onboarding wizard">
          <div style={{ display: "grid", gap: "1rem" }}>
            <div style={{ display: "grid", gap: "0.5rem", gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
              <StepBadge label="Profile" active={currentStep === "profile"} done={status?.profile_completed} />
              <StepBadge label="Sample" active={currentStep === "sample"} done={status?.sample_data_loaded} />
              <StepBadge label="Done" active={currentStep === "done"} done={currentStep === "done"} />
            </div>

            {currentStep === "profile" && (
              <div style={{ display: "grid", gap: "0.75rem" }}>
                <Input
                  label="Logo URL"
                  name="logo_url"
                  value={form.logo_url}
                  onChange={(e) => setForm((prev) => ({ ...prev, logo_url: e.target.value }))}
                  placeholder="https://..."
                />
                <div style={{ display: "grid", gap: "0.5rem", gridTemplateColumns: "repeat(auto-fit, minmax(140px,1fr))" }}>
                  <div>
                    <label style={{ display: "block", fontWeight: 600, color: "#0f172a", marginBottom: "0.35rem" }}>Currency</label>
                    <select
                      value={form.currency}
                      onChange={(e) => setForm((prev) => ({ ...prev, currency: e.target.value }))}
                      style={{ width: "100%", padding: "0.55rem 0.65rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}
                    >
                      {["USD", "EUR", "GBP", "AED", "CAD"].map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                  <Input
                    label="Fiscal year start (MM-DD)"
                    name="fiscal_year_start"
                    value={form.fiscal_year_start}
                    onChange={(e) => setForm((prev) => ({ ...prev, fiscal_year_start: e.target.value }))}
                    placeholder="01-01"
                  />
                  <div>
                    <label style={{ display: "block", fontWeight: 600, color: "#0f172a", marginBottom: "0.35rem" }}>
                      Chart of accounts preset
                    </label>
                    <select
                      value={form.chart_preset}
                      onChange={(e) => setForm((prev) => ({ ...prev, chart_preset: e.target.value }))}
                      style={{ width: "100%", padding: "0.55rem 0.65rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}
                    >
                      <option value="basic">Basic</option>
                      <option value="saas">SaaS</option>
                      <option value="services">Professional Services</option>
                    </select>
                  </div>
                </div>
                <Button onClick={saveProfile} disabled={disabled}>
                  Save & Continue
                </Button>
              </div>
            )}

            {currentStep === "sample" && (
              <div style={{ display: "grid", gap: "0.75rem" }}>
                <p style={{ color: "#475569", margin: 0 }}>
                  Populate this workspace with a few customers and invoices to explore flows. You can remove them later.
                </p>
                <Button onClick={loadSampleData} disabled={disabled || status?.sample_data_loaded}>
                  {status?.sample_data_loaded ? "Sample data ready" : "Create sample data"}
                </Button>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Button variant="ghost" onClick={() => setStatus((prev) => ({ ...prev, step: "profile" }))}>
                    ← Back
                  </Button>
                  <Button onClick={skipSample} variant="secondary" disabled={disabled}>
                    Skip sample
                  </Button>
                </div>
              </div>
            )}

            {currentStep === "done" && (
              <div style={{ display: "grid", gap: "0.75rem" }}>
                <p style={{ color: "#475569", margin: 0 }}>
                  You’re ready! Invite teammates, create your first invoice, or jump into reports.
                </p>
                <div style={{ display: "grid", gap: "0.5rem" }}>
                  <Button onClick={markDone} disabled={disabled}>
                    Mark as complete
                  </Button>
                  <Button variant="ghost" onClick={() => setStatus((prev) => ({ ...prev, step: "profile" }))}>
                    Edit setup
                  </Button>
                </div>
              </div>
            )}
          </div>
        </Card>

        <Card title="Progress">
          <div style={{ display: "grid", gap: "0.5rem", color: "#475569" }}>
            <div>Logo: {status?.logo_url ? "Added" : "Pending"}</div>
            <div>Currency: {status?.currency || "USD"}</div>
            <div>Fiscal year: {status?.fiscal_year_start || "01-01"}</div>
            <div>Chart preset: {status?.chart_preset || "basic"}</div>
            <div>Sample data: {status?.sample_data_loaded ? "Loaded" : "Not loaded"}</div>
          </div>
        </Card>
      </div>
    </MainLayout>
  );
};

export default OnboardingWizard;
