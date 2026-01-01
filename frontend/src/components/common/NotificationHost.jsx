import React from "react";
import useNotifications from "../../hooks/useNotifications.js";

const NotificationHost = () => {
  const { notifications, removeNotification } = useNotifications();

  return (
    <div className="toastHost" role="region" aria-label="Notifications">
      {notifications.map((note) => (
        <div key={note.id} className="toast">
          <div className="toastTitle">{note.title || "Notice"}</div>
          <div className="toastMessage">{note.message}</div>
          <button
            onClick={() => removeNotification(note.id)}
            className="toastDismiss"
            type="button"
          >
            Dismiss
          </button>
        </div>
      ))}
    </div>
  );
};

export default NotificationHost;
