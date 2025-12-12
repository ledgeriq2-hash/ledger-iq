import React from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";

const CustomerPayments = () => {
  const { t } = useTranslation();
  const { portalData } = useOutletContext();
  if (!portalData) {
    return null;
  }
  const items = portalData.payments || [];

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <h2 style={{ marginTop: 0 }}>{t("nav.payments", { defaultValue: "Payments" })}</h2>
      <div className="card" style={{ display: "grid", gap: "0.75rem" }}>
        {items.length === 0 && (
          <p style={{ margin: 0, color: "#64748b" }}>
            {t("status.noData", { defaultValue: "No data available" })}
          </p>
        )}
        {items.map((pay) => (
          <div
            key={pay.id}
            style={{
              padding: "0.75rem",
              border: "1px solid #e2e8f0",
              borderRadius: "10px",
              display: "grid",
              gap: "0.35rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 700 }}>{pay.reference || pay.id}</div>
              <span style={{ color: "#16a34a", fontWeight: 700 }}>{pay.status || "COMPLETED"}</span>
            </div>
            <div style={{ color: "#475569" }}>
              {t("status.success", { defaultValue: "Amount" })}: {pay.amount} · {t("status.success", { defaultValue: "Date" })}:{" "}
              {pay.paid_at || pay.created_at}
            </div>
            <div style={{ color: "#64748b", fontSize: "0.95rem" }}>
              {t("nav.invoices", { defaultValue: "Invoices" })}: {pay.invoice_number || pay.invoice_id || "-"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CustomerPayments;
