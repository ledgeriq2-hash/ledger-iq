import React from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useSettings } from "../../hooks/useSettings.js";
import Card from "../../components/kit/Card.jsx";

const isEnabled = (settings, key) => {
  const ft = settings?.feature_toggles || {};
  const pages = ft?.pages || {};
  if (Object.prototype.hasOwnProperty.call(pages, key)) return Boolean(pages[key]);
  if (Object.prototype.hasOwnProperty.call(ft, key)) return Boolean(ft[key]);
  return true;
};

const DashboardLayout = () => {
  const linkClassName = ({ isActive }) => (isActive ? "kit-button kit-buttonPrimary" : "kit-button kit-buttonGhost");
  const { data } = useSettings();

  return (
    <div className="dashboardShell">
      <div className="kit-container portalGrid">
        <Card
          title="Dashboard"
          headerRight={
            <nav className="dashboardNav">
              <NavLink to="/dashboard" end className={linkClassName}>
                Dashboard
              </NavLink>
              <NavLink to="/predictions" className={linkClassName}>
                Predictions
              </NavLink>
              <NavLink to="/portal" className={linkClassName}>
                Portal
              </NavLink>
              <NavLink to="/customers" className={linkClassName}>
                Customers
              </NavLink>
              {isEnabled(data, "invoices") && isEnabled(data, "dashboard_invoices") ? (
                <NavLink to="/dashboard/invoices" className={linkClassName}>
                  Invoices
                </NavLink>
              ) : null}
              {isEnabled(data, "suppliers") && isEnabled(data, "dashboard_suppliers") ? (
                <NavLink to="/dashboard/suppliers" className={linkClassName}>
                  Suppliers
                </NavLink>
              ) : null}
              {isEnabled(data, "workers") && isEnabled(data, "dashboard_workers") ? (
                <NavLink to="/dashboard/workers" className={linkClassName}>
                  Workers
                </NavLink>
              ) : null}
              {isEnabled(data, "debts") && isEnabled(data, "dashboard_debts") ? (
                <NavLink to="/dashboard/debts" className={linkClassName}>
                  Debts
                </NavLink>
              ) : null}
              <NavLink to="/dashboard/treasury" className={linkClassName}>
                Treasury
              </NavLink>
              {isEnabled(data, "ai") && isEnabled(data, "dashboard_ai") ? (
                <NavLink to="/dashboard/ai" className={linkClassName}>
                  AI
                </NavLink>
              ) : null}
              <NavLink to="/settings" className={linkClassName}>
                Settings
              </NavLink>
            </nav>
          }
        >
          <div className="dashboardMain">
            <Outlet />
          </div>
        </Card>
      </div>
    </div>
  );
};

export default DashboardLayout;
