import React from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Card from "../../../components/ui/Card.jsx";
import Banner from "../../../components/ui/Banner.jsx";
import colors from "../../../design/colors.js";
import spacing from "../../../design/spacing.js";

const CustomerOverview = () => {
  const { t } = useTranslation();
  const { portalData } = useOutletContext();
  if (!portalData) {
    return <Banner message={t("status.noData", { defaultValue: "No portal data available." })} />;
  }

  const invoices = portalData?.invoices || [];
  const payments = portalData?.payments || [];
  const stats = {
    invoices_open: invoices.length,
    payments_made: payments.length,
    anomalies: portalData?.stats?.anomalies ?? 0,
  };
  const recent = portalData?.recent_activity || [];

  return (
    <div style={{ display: "grid", gap: spacing.lg }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: spacing.lg }}>
        <Card>
          <div style={{ color: colors.textMuted, fontWeight: 600 }}>{t("nav.invoices", { defaultValue: "Invoices" })}</div>
          <div style={{ fontSize: "1.8rem", fontWeight: 700 }}>{stats.invoices_open ?? 0}</div>
        </Card>
        <Card>
          <div style={{ color: colors.textMuted, fontWeight: 600 }}>{t("nav.payments", { defaultValue: "Payments" })}</div>
          <div style={{ fontSize: "1.8rem", fontWeight: 700 }}>{stats.payments_made ?? 0}</div>
        </Card>
        <Card>
          <div style={{ color: colors.textMuted, fontWeight: 600 }}>
            {t("ai.anomalies", { defaultValue: "Anomalies" })}
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: 700 }}>{stats.anomalies ?? 0}</div>
        </Card>
      </div>

      <Card title={t("status.success", { defaultValue: "Recent activity" })}>
        <div style={{ display: "grid", gap: spacing.md }}>
          {recent.length === 0 && (
            <Banner message={t("status.noData", { defaultValue: "No data available" })} variant="info" />
          )}
          {recent.map((item) => (
            <div
              key={item.id || item.title}
              style={{ display: "flex", justifyContent: "space-between", gap: spacing.md, alignItems: "center" }}
            >
              <div>
                <div style={{ fontWeight: 600 }}>{item.title}</div>
                <div style={{ color: colors.textMuted }}>{item.description}</div>
              </div>
              <div style={{ color: "#94a3b8", fontSize: "0.9rem" }}>{item.timestamp}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default CustomerOverview;
