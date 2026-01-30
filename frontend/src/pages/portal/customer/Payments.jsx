import React from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";
import StatusPill from "../../../components/kit/StatusPill.jsx";
import Banner from "../../../components/ui/Banner.jsx";

const CustomerPayments = () => {
  const { t } = useTranslation();
  const { portalData } = useOutletContext();
  if (!portalData) {
    return null;
  }
  const items = portalData.payments || [];

  return (
    <div className="portalGrid">
      <h2 className="portalSectionTitle">{t("nav.payments", { defaultValue: "Payments" })}</h2>
      <div className="kit-card portalList">
        {items.length === 0 ? (
          <Banner variant="info" message={t("status.noData", { defaultValue: "No data available" })} />
        ) : (
          items.map((pay) => (
            <div key={pay.id} className="portalListItem">
              <div className="portalListHeader">
                <div style={{ fontWeight: 700 }}>{pay.reference || pay.id}</div>
                <StatusPill tone="success">{pay.status || "COMPLETED"}</StatusPill>
              </div>
              <div className="portalMetaRow">
                {t("status.success", { defaultValue: "Amount" })}: {pay.amount} ·{" "}
                {t("status.success", { defaultValue: "Date" })}: {pay.paid_at || pay.created_at}
              </div>
              <div className="portalMetaRow">
                {t("nav.invoices", { defaultValue: "Invoices" })}: {pay.invoice_number || pay.invoice_id || "-"}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default CustomerPayments;
