import React from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";
import StatusPill from "../../../components/kit/StatusPill.jsx";
import Banner from "../../../components/ui/Banner.jsx";

const SupplierOrders = () => {
  const { t } = useTranslation();
  const { portalData } = useOutletContext();
  if (!portalData) {
    return null;
  }
  const orders = portalData.orders || [];

  return (
    <div className="portalGrid">
      <h2 className="portalSectionTitle">{t("nav.invoices", { defaultValue: "Orders" })}</h2>
      <div className="kit-card portalList">
        {orders.length === 0 ? (
          <Banner variant="info" message={t("status.noData", { defaultValue: "No data available" })} />
        ) : (
          orders.map((order) => (
            <div key={order.id || order.reference} className="portalListItem">
              <div className="portalListHeader">
                <div style={{ fontWeight: 700 }}>{order.reference || order.id}</div>
                <StatusPill tone="info">{order.status || "OPEN"}</StatusPill>
              </div>
              <div className="portalMetaRow">
                {t("status.success", { defaultValue: "Total" })}: {order.total_amount || order.total || "-"}
              </div>
              <div className="portalMetaRow">
                {t("nav.customers", { defaultValue: "Customers" })}: {order.customer_name || "-"}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default SupplierOrders;
