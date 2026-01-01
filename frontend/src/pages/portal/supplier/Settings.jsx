import React from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Card from "../../../components/ui/Card.jsx";

const SupplierSettings = () => {
  const { t } = useTranslation();
  const { portalData } = useOutletContext();

  if (!portalData) {
    return <div>{t("status.loading", { defaultValue: "Loading..." })}</div>;
  }

  const settings = portalData?.settings || {};
  const notificationsEnabled = settings.notifications ?? true;
  const language = settings.language || "en";
  const languageLabel = language === "ar" ? "Arabic" : "English";

  return (
    <div style={{ display: "grid", gap: "1rem", maxWidth: "520px" }}>
      <h2 style={{ marginTop: 0 }}>{t("nav.settings", { defaultValue: "Settings" })}</h2>
      <Card title={t("nav.settings", { defaultValue: "Settings" })} subtitle="Read-only portal view">
        <div style={{ display: "grid", gap: "0.6rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
            <span style={{ color: "var(--color-muted)", fontWeight: 700 }}>
              {t("notifications.title", { defaultValue: "Notifications" })}
            </span>
            <span style={{ color: "var(--color-text)" }}>
              {notificationsEnabled ? t("status.success", { defaultValue: "Enabled" }) : t("status.error", { defaultValue: "Disabled" })}
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
            <span style={{ color: "var(--color-muted)", fontWeight: 700 }}>
              {t("profile.language", { defaultValue: "Preferred language" })}
            </span>
            <span style={{ color: "var(--color-text)" }}>{languageLabel}</span>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default SupplierSettings;
