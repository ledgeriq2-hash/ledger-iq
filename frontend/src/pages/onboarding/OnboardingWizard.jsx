import React, { useEffect, useMemo, useState } from "react";

import { useLocation } from "react-router-dom";
import MainLayout from "../../layouts/MainLayout.jsx";
import Card from "../../components/ui/Card.jsx";
import Input from "../../components/ui/Input.jsx";
import Select from "../../components/ui/Select.jsx";
import Button from "../../components/ui/Button.jsx";
import onboardingApi from "../../api/onboardingApi.js";
import useNotifications from "../../hooks/useNotifications.js";
import useAuth from "../../hooks/useAuth.js";
import StatusPill from "../../components/kit/StatusPill.jsx";
import { TENANT_ERROR_QUERY, TENANT_MISSING_ERROR } from "../../constants/tenantErrors.js";

const StepBadge = ({ label, active, done }) => (
  <div className={`stepBadge ${active ? "isActive" : ""}`.trim()} data-done={done ? "true" : "false"}>
    <span className="stepBadgeDot" aria-hidden="true">
      {done ? "✓" : label[0]}
    </span>
    <span className="stepBadgeText">{label}</span>
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
  const location = useLocation();
  const [tenantErrorNotified, setTenantErrorNotified] = useState(false);

  const tenantErrorCode = useMemo(
    () => new URLSearchParams(location.search).get(TENANT_ERROR_QUERY),
    [location.search]
  );
  const showTenantError = tenantErrorCode === TENANT_MISSING_ERROR.code;

  useEffect(() => {
    if (showTenantError && !tenantErrorNotified) {
      addNotification({
        title: "Tenant required",
        message: TENANT_MISSING_ERROR.message,
      });
      setTenantErrorNotified(true);
    }
  }, [showTenantError, tenantErrorNotified, addNotification]);

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
      <div className="u-flex u-justify-between u-items-center u-wrap u-gap-4 u-m-0 wizardHeader">
        <div className="u-grid u-gap-1">
          <h2 className="u-m-0">Welcome, {tenant?.name || "team"}</h2>
          <p className="u-m-0 u-text-muted">Guide your workspace setup in three quick steps.</p>
        </div>
        {loading && <span className="u-text-muted">Saving...</span>}
      </div>
      {showTenantError ? (
        <div className="u-mt-3">
          <StatusPill tone="danger">{TENANT_MISSING_ERROR.message}</StatusPill>
        </div>
      ) : null}

      <div className="wizardGrid">
        <Card title="Onboarding wizard">
          <div className="u-grid u-gap-4">
            <div className="wizardStepsGrid">
              <StepBadge label="Profile" active={currentStep === "profile"} done={Boolean(status?.profile_completed)} />
              <StepBadge label="Sample" active={currentStep === "sample"} done={Boolean(status?.sample_data_loaded)} />
              <StepBadge label="Done" active={currentStep === "done"} done={currentStep === "done"} />
            </div>

            {currentStep === "profile" && (
              <div className="u-grid u-gap-4">
                <Input
                  label="Logo URL"
                  name="logo_url"
                  value={form.logo_url}
                  onChange={(e) => setForm((prev) => ({ ...prev, logo_url: e.target.value }))}
                  placeholder="https://..."
                />

                <div className="wizardProfileGrid">
                  <Select
                    label="Currency"
                    value={form.currency}
                    onChange={(e) => setForm((prev) => ({ ...prev, currency: e.target.value }))}
                    options={["USD", "EUR", "GBP", "AED", "CAD"].map((c) => ({ label: c, value: c }))}
                  />
                  <Input
                    label="Fiscal year start (MM-DD)"
                    name="fiscal_year_start"
                    value={form.fiscal_year_start}
                    onChange={(e) => setForm((prev) => ({ ...prev, fiscal_year_start: e.target.value }))}
                    placeholder="01-01"
                  />
                  <Select
                    label="Chart of accounts preset"
                    value={form.chart_preset}
                    onChange={(e) => setForm((prev) => ({ ...prev, chart_preset: e.target.value }))}
                    options={[
                      { label: "Basic", value: "basic" },
                      { label: "SaaS", value: "saas" },
                      { label: "Professional Services", value: "services" },
                    ]}
                  />
                </div>

                <Button onClick={saveProfile} disabled={disabled}>
                  Save & Continue
                </Button>
              </div>
            )}

            {currentStep === "sample" && (
              <div className="u-grid u-gap-4">
                <p className="u-text-muted u-m-0">
                  Populate this workspace with a few customers and invoices to explore flows. You can remove them later.
                </p>
                <Button onClick={loadSampleData} disabled={disabled || status?.sample_data_loaded}>
                  {status?.sample_data_loaded ? "Sample data ready" : "Create sample data"}
                </Button>
                <div className="wizardActionsRow">
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
              <div className="u-grid u-gap-4">
                <p className="u-text-muted u-m-0">
                  You’re ready! Invite teammates, create your first invoice, or jump into reports.
                </p>
                <div className="u-grid u-gap-2">
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
          <div className="u-grid u-gap-2 u-text-muted">
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
