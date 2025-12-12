import React from "react";
import useNotifications from "../../hooks/useNotifications.js";

const NotificationHost = () => {
  const { notifications, removeNotification } = useNotifications();

  return (
    <div
      style={{
        position: "fixed",
        top: "1rem",
        right: "1rem",
        display: "grid",
        gap: "0.5rem",
        zIndex: 999,
        maxWidth: "360px",
      }}
    >
      {notifications.map((note) => (
        <div
          key={note.id}
          style={{
            background: "#0f172a",
            color: "#e2e8f0",
            padding: "0.85rem 1rem",
            borderRadius: "10px",
            boxShadow: "0 15px 40px rgba(15,23,42,0.4)",
            border: "1px solid #1e293b",
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: "0.25rem" }}>{note.title || "Notice"}</div>
          <div style={{ fontSize: "0.95rem" }}>{note.message}</div>
          <button
            onClick={() => removeNotification(note.id)}
            style={{
              marginTop: "0.5rem",
              background: "transparent",
              border: "none",
              color: "#38bdf8",
              cursor: "pointer",
              fontWeight: 600,
              padding: 0,
            }}
          >
            Dismiss
          </button>
        </div>
      ))}
    </div>
  );
};

export default NotificationHost;
