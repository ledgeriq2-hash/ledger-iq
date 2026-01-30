import React from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";
import StatusPill from "../../../components/kit/StatusPill.jsx";
import Banner from "../../../components/ui/Banner.jsx";

const CustomerInvoices = () => {
  const { t } = useTranslation();
  const { portalData } = useOutletContext();
  if (!portalData) {
    return null;
  }
  const items = portalData.invoices || [];

  return (
    <div className="portalGrid">
      <h2 className="portalSectionTitle">{t("nav.invoices", { defaultValue: "Invoices" })}</h2>
      <div className="kit-card portalList">
        {items.length === 0 ? (
          <Banner variant="info" message={t("status.noData", { defaultValue: "No data available" })} />
        ) : (
          items.map((inv) => (
            <div key={inv.id || inv.number} className="portalListItem">
              <div className="portalListHeader">
                <div style={{ fontWeight: 700 }}>{inv.number || inv.id}</div>
                <StatusPill tone="info">{inv.status || t("status.loading", { defaultValue: "Pending" })}</StatusPill>
              </div>
              <div className="portalMetaRow">
                {t("portal.customer", { defaultValue: "Customer Portal" })}: {inv.customer_name || "-"}
              </div>
              <div className="portalMetaRow">
                {t("status.success", { defaultValue: "Total" })}: {inv.total_amount || inv.total} ·{" "}
                {t("status.error", { defaultValue: "Due" })}: {inv.due_date || "-"}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default CustomerInvoices;
