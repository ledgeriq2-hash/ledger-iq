import React from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Card from "../../../components/ui/Card.jsx";
import Banner from "../../../components/ui/Banner.jsx";

const CustomerOverview = () => {
  const { t } = useTranslation();
  const { portalData } = useOutletContext();
  if (!portalData) {
    return <Banner message={t("status.noData", { defaultValue: "No portal data available." })} />;
  }

  const invoices = portalData?.invoices || [];
  const payments = portalData?.payments || [];
  const stats = {
    invoices_open: portalData?.stats?.open_invoices ?? invoices.length,
    payments_made: payments.length,
    total_outstanding: portalData?.stats?.total_open_amount ?? 0,
  };
  const recent = portalData?.recent_activity || [];

  const balance = portalData?.balance;

  return (
    <div className="portalGrid">
      <div className="portalStats">
        <Card>
          <div className="portalStatLabel">{t("nav.invoices", { defaultValue: "Invoices" })}</div>
          <div className="portalStatValue">{stats.invoices_open ?? 0}</div>
        </Card>
        <Card>
          <div className="portalStatLabel">{t("nav.payments", { defaultValue: "Payments" })}</div>
          <div className="portalStatValue">{stats.payments_made ?? 0}</div>
        </Card>
        <Card>
          <div className="portalStatLabel">
            {t("portal.stats.totalOpenAmount", { defaultValue: "Total outstanding" })}
          </div>
          <div className="portalStatValue">{stats.total_outstanding ?? 0}</div>
        </Card>
        {balance ? (
          <Card>
            <div className="portalStatLabel">{t("portal.balance", { defaultValue: "Current balance" })}</div>
            <div className="portalStatValue">{balance.balance}</div>
            <div className="kit-muted">{balance.as_of_date}</div>
          </Card>
        ) : null}
      </div>

      <Card title={t("status.success", { defaultValue: "Recent activity" })}>
        <div className="portalList">
          {recent.length === 0 ? (
            <Banner message={t("status.noData", { defaultValue: "No data available" })} variant="info" />
          ) : (
            recent.map((item) => (
              <div key={item.id || item.title} className="portalListItem">
                <div className="portalListHeader">
                  <div>
                    <div style={{ fontWeight: 600 }}>{item.title}</div>
                    <div className="kit-muted">{item.description}</div>
                  </div>
                  <div className="kit-muted">{item.timestamp}</div>
                </div>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
};

export default CustomerOverview;
