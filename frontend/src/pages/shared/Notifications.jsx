import React from "react";
import { useTranslation } from "react-i18next";

import LoadingSpinner from "../../components/common/LoadingSpinner.jsx";
import Card from "../../components/ui/Card.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";
import { useMarkNotificationRead, useNotificationsQuery } from "../../hooks/useNotifications.js";

const Notifications = () => {
  const { t } = useTranslation();
  const notificationsQuery = useNotificationsQuery();
  const markRead = useMarkNotificationRead();

  const items = notificationsQuery.data?.items || [];

  if (notificationsQuery.isLoading) {
    return <LoadingSpinner message={t("status.loading", { defaultValue: "Loading notifications..." })} />;
  }

  if (notificationsQuery.isError) {
    return (
      <div className="u-pad-4">
        <ErrorState
          title={t("status.error", { defaultValue: "Failed to load notifications." })}
          error={notificationsQuery.error}
          onRetry={notificationsQuery.refetch}
        />
      </div>
    );
  }

  return (
    <div className="u-pad-4 u-grid u-gap-4">
      <h1 className="u-m-0">{t("nav.notifications", { defaultValue: "Notifications" })}</h1>
      <Card>
        {items.length === 0 ? (
          <EmptyState
            title={t("notifications.empty", { defaultValue: "No notifications yet." })}
            message={t("notifications.emptyMessage", { defaultValue: "You're all caught up." })}
          />
        ) : null}
        <div className="notificationsList">
          {items.map((note) => {
            const isRead = note.read || note.is_read;
            return (
              <div key={note.id} className={`notificationItem ${isRead ? "isRead" : "isUnread"}`.trim()}>
                <div className="notificationHeader">
                  <div className="notificationTitle">
                    {note.title || t("notifications.title", { defaultValue: "Notification" })}
                  </div>
                  {!isRead && (
                    <button
                      type="button"
                      onClick={() => markRead.mutate(note.id)}
                      disabled={markRead.isPending}
                      className="controlButton"
                    >
                      {t("notifications.markRead", { defaultValue: "Mark as read" })}
                    </button>
                  )}
                </div>
                <div className="notificationBody">{note.message || note.body || note.description}</div>
                <div className="notificationMeta">{note.created_at}</div>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
};

export default Notifications;
