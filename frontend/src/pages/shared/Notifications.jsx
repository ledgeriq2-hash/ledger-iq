import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import httpClient from "../../api/httpClient";
import LoadingSpinner from "../../components/common/LoadingSpinner.jsx";

const Notifications = () => {
  const { t } = useTranslation();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updating, setUpdating] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await httpClient.get("/me/notifications");
      setItems(res.data?.items || res.data || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const markRead = async (id) => {
    setUpdating(true);
    try {
      await httpClient.post(`/me/notifications/${id}/read`);
      setItems((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true, is_read: true } : n))
      );
    } catch (err) {
      setError(err);
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message={t("status.loading", { defaultValue: "Loading notifications..." })} />;
  }

  if (error) {
    return (
      <div style={{ padding: "1rem" }}>
        <p style={{ color: "#b91c1c" }}>{t("status.error", { defaultValue: "Failed to load notifications." })}</p>
        <pre style={{ background: "#fef2f2", padding: "0.75rem", borderRadius: "8px", overflow: "auto" }}>
          {error?.message}
        </pre>
      </div>
    );
  }

  return (
    <div style={{ padding: "1rem", display: "grid", gap: "1rem" }}>
      <h1 style={{ margin: 0 }}>{t("nav.notifications", { defaultValue: "Notifications" })}</h1>
      <div className="card" style={{ display: "grid", gap: "0.75rem" }}>
        {items.length === 0 && (
          <p style={{ margin: 0, color: "#64748b" }}>
            {t("notifications.empty", { defaultValue: "No notifications yet." })}
          </p>
        )}
        {items.map((note) => {
          const isRead = note.read || note.is_read;
          return (
            <div
              key={note.id}
              style={{
                padding: "0.75rem",
                borderRadius: "10px",
                border: "1px solid #e2e8f0",
                background: isRead ? "#f8fafc" : "#eef2ff",
                display: "grid",
                gap: "0.3rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem" }}>
                <div style={{ fontWeight: 600 }}>{note.title || t("notifications.title", { defaultValue: "Notification" })}</div>
                {!isRead && (
                  <button
                    type="button"
                    onClick={() => markRead(note.id)}
                    disabled={updating}
                    style={{
                      padding: "0.35rem 0.65rem",
                      borderRadius: "8px",
                      border: "1px solid #cbd5e1",
                      background: "#e0f2fe",
                      cursor: "pointer",
                    }}
                  >
                    {t("notifications.markRead", { defaultValue: "Mark as read" })}
                  </button>
                )}
              </div>
              <div style={{ color: "#475569" }}>{note.body || note.description}</div>
              <div style={{ color: "#94a3b8", fontSize: "0.9rem" }}>{note.created_at}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Notifications;
