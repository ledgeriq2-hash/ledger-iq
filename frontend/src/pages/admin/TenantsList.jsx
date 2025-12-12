import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import MainLayout from "../../layouts/MainLayout.jsx";
import adminApi from "../../api/adminApi.js";
import usePermissions from "../../hooks/usePermissions.js";

const TenantsList = () => {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const { hasRole } = usePermissions();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.listTenants();
      setTenants(data || []);
    } catch (err) {
      setError("Failed to load tenants");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const toggleSoftLaunch = async (tenantId, enabled) => {
    try {
      if (enabled) {
        await adminApi.enableSoftLaunch(tenantId);
      } else {
        await adminApi.disableSoftLaunch(tenantId);
      }
      await load();
    } catch {
      setError("Unable to update soft launch flag");
    }
  };

  if (!hasRole("owner") && !hasRole("admin")) {
    return (
      <MainLayout>
        <div>You need admin or owner permissions to view this page.</div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2 style={{ margin: 0 }}>Tenants</h2>
        {loading && <span style={{ color: "#475569" }}>Loading...</span>}
      </div>
      {error && <div style={{ color: "#b91c1c", marginBottom: "0.75rem" }}>{error}</div>}
      <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: "10px", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead style={{ background: "#f8fafc" }}>
            <tr>
              {["Name", "Slug", "Created", "Owner", "Plan", "Status", "Soft Launch", "Actions"].map((h) => (
                <th
                  key={h}
                  style={{ textAlign: "left", padding: "0.75rem", borderBottom: "1px solid #e2e8f0", fontWeight: 600 }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tenants.map((t) => (
              <tr key={t.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                <td style={{ padding: "0.75rem" }}>{t.name}</td>
                <td style={{ padding: "0.75rem" }}>{t.slug}</td>
                <td style={{ padding: "0.75rem" }}>{new Date(t.created_at).toLocaleDateString()}</td>
                <td style={{ padding: "0.75rem" }}>{t.owner_email || "—"}</td>
                <td style={{ padding: "0.75rem" }}>{t.plan_code || "—"}</td>
                <td style={{ padding: "0.75rem" }}>{t.subscription_status || "inactive"}</td>
                <td style={{ padding: "0.75rem" }}>{t.is_soft_launch ? "Yes" : "No"}</td>
                <td style={{ padding: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <button
                    onClick={() => navigate(`/admin/tenants/${t.id}`)}
                    style={{ padding: "0.35rem 0.6rem", borderRadius: "6px", border: "1px solid #cbd5e1" }}
                  >
                    Overview
                  </button>
                  <button
                    onClick={() => toggleSoftLaunch(t.id, true)}
                    style={{
                      padding: "0.35rem 0.6rem",
                      borderRadius: "6px",
                      border: "1px solid #22c55e",
                      color: "#166534",
                    }}
                  >
                    Enable
                  </button>
                  <button
                    onClick={() => toggleSoftLaunch(t.id, false)}
                    style={{
                      padding: "0.35rem 0.6rem",
                      borderRadius: "6px",
                      border: "1px solid #ef4444",
                      color: "#b91c1c",
                    }}
                  >
                    Disable
                  </button>
                </td>
              </tr>
            ))}
            {!tenants.length && (
              <tr>
                <td style={{ padding: "0.75rem" }} colSpan={8}>
                  No tenants found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </MainLayout>
  );
};

export default TenantsList;
