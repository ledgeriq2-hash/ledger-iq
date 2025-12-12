import React, { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import portalApi from "../../api/portalApi";
import LoadingSpinner from "../../components/common/LoadingSpinner.jsx";
import { getPortalToken, setPortalToken } from "../../api/httpClient";
import Card from "../../components/ui/Card.jsx";
import Banner from "../../components/ui/Banner.jsx";
import ErrorBox from "../../components/ui/ErrorBox.jsx";
import colors from "../../design/colors.js";
import spacing from "../../design/spacing.js";

const navStyle = (isActive) => ({
  padding: "0.55rem 0.85rem",
  borderRadius: "10px",
  textDecoration: "none",
  color: isActive ? colors.primary : colors.text,
  background: isActive ? "rgba(14,165,233,0.08)" : "transparent",
  fontWeight: 600,
  border: isActive ? `1px solid ${colors.primary}` : `1px solid transparent`,
});

const CustomerPortal = () => {
  const { token } = useParams();
  const [portalToken, setPortalTokenState] = useState(() => token || getPortalToken());

  useEffect(() => {
    if (token && token !== portalToken) {
      setPortalTokenState(token);
      setPortalToken(token);
    }
  }, [token, portalToken]);

  const activeToken = useMemo(() => portalToken || getPortalToken(), [portalToken]);

  const { data: portalData, isLoading, error } = useQuery({
    queryKey: ["portal", "customer", activeToken],
    queryFn: async () => {
      const [overview, invoices, payments, settings] = await Promise.all([
        portalApi.customerOverview(activeToken),
        portalApi.customerInvoices(activeToken),
        portalApi.customerPayments(activeToken),
        portalApi.customerSettings(activeToken),
      ]);
      return {
        ...overview,
        invoices: invoices?.invoices || overview?.invoices || [],
        payments: payments?.payments || overview?.payments || [],
        settings: settings || overview?.settings || {},
      };
    },
    enabled: Boolean(activeToken),
    retry: 2,
  });

  const renderBody = () => {
    if (!activeToken) {
      return <Banner variant="danger" title="Missing portal token" message="Request a new secure link." />;
    }
    if (isLoading) {
      return <LoadingSpinner message="Loading customer portal..." />;
    }
    if (error) {
      return <ErrorBox message={error.message || "Failed to load portal."} />;
    }
    return <Outlet context={{ token: activeToken, portalData }} />;
  };

  const base = ".";

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, rgba(14,165,233,0.08), rgba(15,23,42,0.94))",
        padding: "1rem",
        color: "#0f172a",
      }}
      data-testid="customer-portal"
    >
      <div style={{ maxWidth: "1080px", margin: "0 auto", display: "grid", gap: "1rem" }}>
        <Card
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderRadius: "14px",
          }}
        >
          <div>
            <h2 style={{ margin: 0, color: colors.text }}>Customer Portal</h2>
            <p style={{ margin: 0, color: colors.textMuted, fontSize: "0.95rem" }}>Secure link access</p>
          </div>
          <nav style={{ display: "flex", gap: spacing.sm, flexWrap: "wrap" }}>
            <NavLink to={`${base}`} end style={({ isActive }) => navStyle(isActive)}>
              Overview
            </NavLink>
            <NavLink to={`${base}/invoices`} style={({ isActive }) => navStyle(isActive)}>
              Invoices
            </NavLink>
            <NavLink to={`${base}/payments`} style={({ isActive }) => navStyle(isActive)}>
              Payments
            </NavLink>
            <NavLink to={`${base}/settings`} style={({ isActive }) => navStyle(isActive)}>
              Settings
            </NavLink>
          </nav>
        </Card>

        <main>{renderBody()}</main>
      </div>
    </div>
  );
};

export default CustomerPortal;
