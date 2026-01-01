import React from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";

const SupplierPayments = () => {
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
          <p style={{ margin: 0, color: "var(--color-muted)" }}>
            {t("status.noData", { defaultValue: "No data available" })}
          </p>
        )}
        {items.map((pay) => (
          <div
            key={pay.id}
            style={{
              padding: "0.75rem",
              border: "1px solid var(--color-border)",
              borderRadius: "10px",
              display: "grid",
              gap: "0.35rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 700 }}>{pay.reference || pay.id}</div>
              <span style={{ color: "var(--color-primary)", fontWeight: 700 }}>{pay.status || "COMPLETED"}</span>
            </div>
            <div style={{ color: "var(--color-muted)" }}>
              {t("status.success", { defaultValue: "Amount" })}: {pay.amount} · {t("status.success", { defaultValue: "Date" })}:{" "}
              {pay.paid_at || pay.created_at}
            </div>
            <div style={{ color: "var(--color-muted)", fontSize: "0.95rem" }}>
              {t("nav.suppliers", { defaultValue: "Suppliers" })}: {pay.supplier_name || "-"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SupplierPayments;
