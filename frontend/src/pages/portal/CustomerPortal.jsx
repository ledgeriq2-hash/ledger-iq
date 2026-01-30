import React, { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useParams } from "react-router-dom";
import { useCustomerPortalData } from "../../hooks/usePortalData.js";
import LoadingSpinner from "../../components/common/LoadingSpinner.jsx";
import { getPortalToken, setPortalToken } from "../../utils/portalTokens.js";
import Card from "../../components/ui/Card.jsx";
import Banner from "../../components/ui/Banner.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";

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
    <div className="portalPage" data-testid="customer-portal">
      <div className="kit-container portalGrid">
        <Card className="portalNavCard">
          <div>
            <h2 className="portalSectionTitle">Customer Portal</h2>
            <p className="kit-muted" style={{ margin: 0 }}>
              Secure link access
            </p>
          </div>
          <nav className="portalTabs">
            <NavLink to={`${base}`} end className={({ isActive }) => `portalTab ${isActive ? "isActive" : ""}`}>
              Overview
            </NavLink>
            <NavLink to={`${base}/invoices`} className={({ isActive }) => `portalTab ${isActive ? "isActive" : ""}`}>
              Invoices
            </NavLink>
            <NavLink to={`${base}/payments`} className={({ isActive }) => `portalTab ${isActive ? "isActive" : ""}`}>
              Payments
            </NavLink>
            <NavLink to={`${base}/settings`} className={({ isActive }) => `portalTab ${isActive ? "isActive" : ""}`}>
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
