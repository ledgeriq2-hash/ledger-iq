import React from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";

const SupplierOrders = () => {
  const { t } = useTranslation();
  const { portalData } = useOutletContext();
  if (!portalData) {
    return null;
  }
  const orders = portalData.orders || [];

  return (
    <div style={{ display: "grid", gap: "1rem" }}>
      <h2 style={{ marginTop: 0 }}>{t("nav.invoices", { defaultValue: "Orders" })}</h2>
      <div className="card" style={{ display: "grid", gap: "0.75rem" }}>
        {orders.length === 0 && (
          <p style={{ margin: 0, color: "#64748b" }}>
            {t("status.noData", { defaultValue: "No data available" })}
          </p>
        )}
        {orders.map((order) => (
          <div
            key={order.id || order.reference}
            style={{
              padding: "0.75rem",
              border: "1px solid #e2e8f0",
              borderRadius: "10px",
              display: "grid",
              gap: "0.35rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 700 }}>{order.reference || order.id}</div>
              <span style={{ color: "#475569" }}>{order.status || "OPEN"}</span>
            </div>
            <div style={{ color: "#475569" }}>
              {t("status.success", { defaultValue: "Total" })}: {order.total_amount || order.total || "-"}
            </div>
            <div style={{ color: "#64748b", fontSize: "0.95rem" }}>
              {t("nav.customers", { defaultValue: "Customers" })}: {order.customer_name || "-"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SupplierOrders;
