import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import Card from "../../components/ui/Card.jsx";
import Input from "../../components/ui/Input.jsx";
import Button from "../../components/ui/Button.jsx";
import useAuth from "../../hooks/useAuth.js";

const getTenantId = () =>
  (typeof window !== "undefined" ? localStorage.getItem("tenant_id") : null) || import.meta.env.VITE_TENANT_ID;

const TenantSelect = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { setTenantId } = useAuth();

  const existingTenantId = useMemo(() => getTenantId(), []);
  const [tenantIdInput, setTenantIdInput] = useState(existingTenantId || "");
  const [error, setError] = useState("");

  useEffect(() => {
    if (existingTenantId) navigate("/dashboard", { replace: true });
  }, [existingTenantId, navigate]);

  const onSave = (event) => {
    event.preventDefault();
    const value = String(tenantIdInput || "").trim();
    if (!value) {
      setError("Please enter a tenant id.");
      return;
    }

    setTenantId(value);
    setError("");

    const redirectTo = location.state?.from || "/dashboard";
    navigate(redirectTo, { replace: true });
  };

  return (
    <div className="u-grid u-place-center" style={{ minHeight: "70vh" }}>
      <div className="u-w-full" style={{ maxWidth: 520 }}>
        <Card title="Select tenant" subtitle="Enter the tenant id to continue">
          <form className="u-grid u-gap-3" onSubmit={onSave}>
            <Input
              label="Tenant ID"
              value={tenantIdInput}
              onChange={(e) => setTenantIdInput(e.target.value)}
              placeholder="e.g. demo"
              autoFocus
              error={error}
              data-testid="tenant-id-input"
            />
            <div className="u-flex u-justify-end">
              <Button type="submit" data-testid="tenant-save-button">
                Save
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
};

export default TenantSelect;
