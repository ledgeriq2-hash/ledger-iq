import React from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Card from "../../../components/ui/Card.jsx";

const CustomerSettings = () => {
  const { t } = useTranslation();
  const { portalData } = useOutletContext();

  if (!portalData) {
    return <div>{t("status.loading", { defaultValue: "Loading..." })}</div>;
  }

  const stats = portalData.stats || {};
  const balance = portalData.balance;
  const balanceDisplay = balance ? `${balance.balance} (${balance.as_of_date})` : t("status.loading", { defaultValue: "Loading..." });

  return (
    <div style={{ display: "grid", gap: "1rem", maxWidth: "520px" }}>
      <h2 style={{ marginTop: 0 }}>{t("nav.settings", { defaultValue: "Settings" })}</h2>
      <Card title={t("nav.settings", { defaultValue: "Settings" })} subtitle="Read-only portal view">
        <div style={{ display: "grid", gap: "0.6rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
            <span style={{ color: "var(--color-muted)", fontWeight: 700 }}>
              {t("portal.stats.openInvoices", { defaultValue: "Open invoices" })}
            </span>
            <span style={{ color: "var(--color-text)", fontWeight: 700 }}>{stats.open_invoices ?? 0}</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
            <span style={{ color: "var(--color-muted)", fontWeight: 700 }}>
              {t("portal.stats.totalOpenAmount", { defaultValue: "Total outstanding" })}
            </span>
            <span style={{ color: "var(--color-text)", fontWeight: 700 }}>
              {stats.total_open_amount ?? 0}
            </span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
            <span style={{ color: "var(--color-muted)", fontWeight: 700 }}>
              {t("portal.balance", { defaultValue: "Current balance" })}
            </span>
            <span style={{ color: "var(--color-text)", fontWeight: 700 }}>{balanceDisplay}</span>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default CustomerSettings;
