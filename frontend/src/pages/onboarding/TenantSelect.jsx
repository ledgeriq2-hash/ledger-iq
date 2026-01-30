import React, { useEffect, useMemo, useRef, useState } from "react";
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
  const autoSelectRef = useRef(false);
  const redirectTo = location.state?.from || "/dashboard";

  const storedTenantId = useMemo(() => getTenantId(), []);
  const [tenantIdInput, setTenantIdInput] = useState(storedTenantId || "");
  const [error, setError] = useState("");
  const [tenants, setTenants] = useState([]);
  const [loadingTenants, setLoadingTenants] = useState(true);

  useEffect(() => {
    if (tenantId) navigate(redirectTo, { replace: true });
  }, [tenantId, redirectTo, navigate]);

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
        setLoadingTenants(false);
      })
      .catch(() => {
        if (active) {
          setTenants([]);
          setLoadingTenants(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (autoSelectRef.current || tenantId || loadingTenants) return;
    if (tenants.length === 1) {
      autoSelectRef.current = true;
      setTenantId(tenants[0].id);
      setError("");
      navigate(redirectTo, { replace: true });
    }
  }, [tenantId, loadingTenants, tenants, setTenantId, navigate, redirectTo]);

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

    navigate(redirectTo, { replace: true });
  };

  const handleSelectTenant = (tenantId) => {
    setTenantId(tenantId);
    setError("");
    navigate(redirectTo, { replace: true });
  };

  if (loadingTenants && !tenantId) {
    return (
      <div className="u-grid u-place-center" style={{ minHeight: "70vh" }}>
        <div className="u-w-full" style={{ maxWidth: 520 }}>
          <Card title="Loading tenants" subtitle="Fetching available tenants..." />
        </div>
      </div>
    );
  }

  if (!tenantId && tenants.length === 1) {
    return (
      <div className="u-grid u-place-center" style={{ minHeight: "70vh" }}>
        <div className="u-w-full" style={{ maxWidth: 520 }}>
          <Card title="Selecting tenant" subtitle="One tenant found. Redirecting..." />
        </div>
      </div>
    );
  }

  const showSelector = tenants.length > 1;
  const showEmpty = !loadingTenants && tenants.length === 0;

  return (
    <div className="u-grid u-place-center" style={{ minHeight: "70vh" }}>
      <div className="u-w-full" style={{ maxWidth: 520 }}>
        <Card title="Select tenant" subtitle="Enter the tenant id to continue">
          {showEmpty ? (
            <div className="u-grid u-gap-3">
              <div className="u-text-muted">No tenants found.</div>
              <div className="u-flex u-justify-end">
                <Button type="button" onClick={() => window.location.reload()}>
                  Reload
                </Button>
              </div>
            </div>
          ) : (
            <>
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
              {showSelector ? (
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
            </>
          )}
        </Card>
      </div>
    </div>
  );
};

export default TenantSelect;
