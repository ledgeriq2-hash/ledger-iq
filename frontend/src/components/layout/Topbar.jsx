import React, { useMemo } from "react";
import { Link, useLocation } from "react-router-dom";

import DateRangeSelector from "./DateRangeSelector.jsx";
import LanguageSwitcher from "./LanguageSwitcher.jsx";
import TenantSelector from "./TenantSelector.jsx";

const labelMap = {
  dashboard: "Dashboard",
  treasury: "Treasury",
  ai: "AI",
  customers: "Customers",
  invoices: "Invoices",
  payments: "Payments",
  inventory: "Inventory",
  employees: "Employees",
  suppliers: "Suppliers",
  reports: "Reports",
  settings: "Settings",
  admin: "Admin",
  notifications: "Notifications",
  portal: "Portal",
};

const isIdSegment = (value) => /^[0-9a-f-]{8,}$/i.test(value) || value.length > 18;

const formatSegment = (segment, prevSegment) => {
  if (!segment) return "";
  if (prevSegment === "portal") return "Access";
  if (isIdSegment(segment)) return "Details";
  if (labelMap[segment]) return labelMap[segment];
  return segment.replace(/-/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
};

const Topbar = ({ onMobileMenu, sidebarCollapsed }) => {
  const location = useLocation();

  const crumbs = useMemo(() => {
    const segments = (location?.pathname || "/").split("/").filter(Boolean);
    return segments.map((segment, index) => {
      const prev = segments[index - 1];
      return {
        label: formatSegment(segment, prev),
        to: `/${segments.slice(0, index + 1).join("/")}`,
      };
    });
  }, [location?.pathname]);

  const title = useMemo(() => (crumbs.length ? crumbs[crumbs.length - 1].label : "Ledger IQ"), [crumbs]);

  return (
    <header className="topbar">
      <div className="topbarLeft">
        <button
          type="button"
          className="iconButton topbarMenuButton"
          onClick={() => {
            onMobileMenu?.();
          }}
          aria-label={sidebarCollapsed ? "Open navigation" : "Toggle navigation"}
        >
          <span aria-hidden="true">≡</span>
        </button>
        <div className="topbarTitleGroup">
          <div className="topbarTitle">{title}</div>
          {crumbs.length ? (
            <nav className="topbarBreadcrumbs" aria-label="Breadcrumb">
              <ol className="breadcrumbsList">
                {crumbs.map((crumb, idx) => {
                  const isLast = idx === crumbs.length - 1;
                  return (
                    <li key={crumb.to} className="breadcrumbItem">
                      {isLast ? (
                        <span className="breadcrumbLabel">{crumb.label}</span>
                      ) : (
                        <Link to={crumb.to} className="breadcrumbLink">
                          {crumb.label}
                        </Link>
                      )}
                      {!isLast ? <span className="breadcrumbSep">/</span> : null}
                    </li>
                  );
                })}
              </ol>
            </nav>
          ) : null}
        </div>
      </div>

      <div className="topbarRight">
        <TenantSelector />
        <div className="topbarCluster">
          <DateRangeSelector />
          <LanguageSwitcher />
        </div>
        <div className="userMenuPlaceholder" role="button" aria-label="User menu">
          <span className="userMenuAvatar" aria-hidden="true" />
          <span>Account</span>
        </div>
      </div>
    </header>
  );
};

export default Topbar;
