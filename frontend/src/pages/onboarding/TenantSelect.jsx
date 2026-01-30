import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import Card from "../../components/ui/Card.jsx";
import Input from "../../components/ui/Input.jsx";
import Button from "../../components/ui/Button.jsx";
import axiosClient from "../../api/index.js";
import useAuth from "../../hooks/useAuth.js";

const getTenantId = () =>
  (typeof window !== "undefined" ? localStorage.getItem("tenant_id") : null) || import.meta.env.VITE_TENANT_ID;

const isUuid = (value) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);

const TenantSelect = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { tenantId, setTenantId } = useAuth();

  const existingTenantId = useMemo(() => getTenantId(), []);
  const [tenantIdInput, setTenantIdInput] = useState(existingTenantId || "");
  const [error, setError] = useState("");
  const [tenants, setTenants] = useState([]);

  useEffect(() => {
    if (tenantId || existingTenantId) navigate("/dashboard", { replace: true });
  }, [tenantId, existingTenantId, navigate]);

  useEffect(() => {
    let active = true;
    axiosClient
      .request({
        method: "GET",
        url: "/v1/dev/tenants",
        skipTenant: true,
        skipAuth: true,
      })
      .then((res) => {
        if (!active) return;
        const items = Array.isArray(res?.data?.items) ? res.data.items : [];
        setTenants(items);
      })
      .catch(() => {
        if (active) setTenants([]);
      });
    return () => {
      active = false;
    };
  }, []);

  const onSave = (event) => {
    event.preventDefault();
    const value = String(tenantIdInput || "").trim();
    if (!value) {
      setError("Please enter a tenant id.");
      return;
    }
    if (!isUuid(value)) {
      setError("Tenant ID must be a valid UUID.");
      return;
    }
    if (tenants.length && !tenants.some((tenant) => tenant.id === value)) {
      setError("Unknown tenant id. Please select from the list or seed a demo tenant.");
      return;
    }

    setTenantId(value);
    setError("");

    const redirectTo = location.state?.from || "/dashboard";
    navigate(redirectTo, { replace: true });
  };

  const handleSelectTenant = (tenantId) => {
    setTenantId(tenantId);
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
          {tenants.length ? (
            <div className="u-grid u-gap-2 u-mt-3">
              <div className="u-text-muted">Quick select (dev only)</div>
              <div className="u-flex u-wrap u-gap-2">
                {tenants.map((tenant) => (
                  <Button
                    key={tenant.id}
                    type="button"
                    variant="ghost"
                    onClick={() => handleSelectTenant(tenant.id)}
                  >
                    {tenant.name} ({tenant.slug})
                  </Button>
                ))}
              </div>
            </div>
          ) : null}
        </Card>
      </div>
    </div>
  );
};

export default TenantSelect;
