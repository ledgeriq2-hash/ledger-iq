import React, { useEffect, useState } from "react";
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
    return <div className="u-pad-4">You need admin or owner permissions to view this page.</div>;
  }

  return (
    <div className="u-pad-4">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2 style={{ margin: 0 }}>Feedback</h2>
        {loading && <span style={{ color: "var(--color-muted)" }}>Loading...</span>}
      </div>
      {error && <div style={{ color: "var(--color-primary)", marginBottom: "0.75rem" }}>{error}</div>}
      <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "10px", overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead style={{ background: "var(--kit-surface-muted)" }}>
            <tr>
              {["Tenant", "User", "Category", "Message", "When"].map((h) => (
                <th
                  key={h}
                  style={{ textAlign: "left", padding: "0.75rem", borderBottom: "1px solid var(--color-border)", fontWeight: 600 }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {items.map((f) => (
              <tr key={f.id} style={{ borderBottom: "1px solid var(--color-border)" }}>
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
    </div>
  );
};

export default FeedbackList;
