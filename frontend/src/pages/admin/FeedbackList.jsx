import React, { useEffect, useState } from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import adminApi from "../../api/adminApi.js";
import usePermissions from "../../hooks/usePermissions.js";

const FeedbackList = () => {
  const [items, setItems] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { hasRole } = usePermissions();

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.adminFeedback({ limit: 200 });
      setItems(data.items || []);
    } catch (err) {
      setError("Failed to load feedback");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

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
        <h2 style={{ margin: 0 }}>Feedback</h2>
        {loading && <span style={{ color: "#475569" }}>Loading...</span>}
      </div>
      {error && <div style={{ color: "#b91c1c", marginBottom: "0.75rem" }}>{error}</div>}
      <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: "10px", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead style={{ background: "#f8fafc" }}>
            <tr>
              {["Tenant", "User", "Category", "Message", "When"].map((h) => (
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
            {items.map((f) => (
              <tr key={f.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                <td style={{ padding: "0.75rem" }}>{f.tenant_id || "—"}</td>
                <td style={{ padding: "0.75rem" }}>{f.user_id || "—"}</td>
                <td style={{ padding: "0.75rem", textTransform: "capitalize" }}>{f.category}</td>
                <td style={{ padding: "0.75rem" }}>{f.message}</td>
                <td style={{ padding: "0.75rem" }}>{new Date(f.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {!items.length && (
              <tr>
                <td style={{ padding: "0.75rem" }} colSpan={5}>
                  No feedback yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </MainLayout>
  );
};

export default FeedbackList;
