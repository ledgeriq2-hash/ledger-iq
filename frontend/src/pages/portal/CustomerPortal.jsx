import React, { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useParams } from "react-router-dom";
import { useCustomerPortalData } from "../../hooks/usePortalData.js";
import LoadingSpinner from "../../components/common/LoadingSpinner.jsx";
import { getPortalToken, setPortalToken } from "../../utils/portalTokens.js";
import Card from "../../components/ui/Card.jsx";
import Banner from "../../components/ui/Banner.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";
import colors from "../../design/colors.js";
import spacing from "../../design/spacing.js";

const navStyle = (isActive) => ({
  padding: "0.55rem 0.85rem",
  borderRadius: "10px",
  textDecoration: "none",
  color: isActive ? colors.primary : colors.text,
  background: isActive ? "color-mix(in srgb, var(--color-primary) 12%, transparent)" : "transparent",
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

  const { data: portalData, isLoading, error, refetch: refreshPortal } = useCustomerPortalData(activeToken);

  const renderBody = () => {
    if (!activeToken) {
      return <Banner variant="danger" title="Missing portal token" message="Request a new secure link." />;
    }
    if (isLoading) {
      return <LoadingSpinner message="Loading customer portal..." />;
    }
    if (error) {
      return (
        <div className="u-pad-4">
          <ErrorState title="Failed to load portal" error={error} onRetry={() => refreshPortal?.()} />
        </div>
      );
    }
    return <Outlet context={{ token: activeToken, portalData }} />;
  };

  const base = ".";

  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "linear-gradient(135deg, color-mix(in srgb, var(--color-secondary) 18%, transparent), var(--color-bg))",
        padding: "1rem",
        color: "var(--color-text)",
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
