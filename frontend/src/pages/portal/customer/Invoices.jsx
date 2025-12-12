import React from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";

const CustomerInvoices = () => {
  const { t } = useTranslation();
  const { portalData } = useOutletContext();
  if (!portalData) {
    return null;
  }
  const items = portalData.invoices || [];

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <h2 style={{ marginTop: 0 }}>{t("nav.invoices", { defaultValue: "Invoices" })}</h2>
      <div className="card" style={{ display: "grid", gap: "0.75rem" }}>
        {items.length === 0 && (
          <p style={{ margin: 0, color: "#64748b" }}>
            {t("status.noData", { defaultValue: "No data available" })}
          </p>
        )}
        {items.map((inv) => (
          <div
            key={inv.id || inv.number}
            style={{
              padding: "0.75rem",
              border: "1px solid #e2e8f0",
              borderRadius: "10px",
              display: "grid",
              gap: "0.35rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 700 }}>{inv.number || inv.id}</div>
              <span style={{ color: "#475569" }}>{inv.status || t("status.loading", { defaultValue: "Pending" })}</span>
            </div>
            <div style={{ color: "#475569" }}>
              {t("portal.customer", { defaultValue: "Customer Portal" })}: {inv.customer_name || "-"}
            </div>
            <div style={{ color: "#64748b", fontSize: "0.95rem" }}>
              {t("status.success", { defaultValue: "Total" })}: {inv.total_amount || inv.total} ·{" "}
              {t("status.error", { defaultValue: "Due" })}: {inv.due_date || "-"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CustomerInvoices;
