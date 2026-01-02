import React from "react";
import { NavLink } from "react-router-dom";

import {
  IconAdmin,
  IconAI,
  IconCustomers,
  IconDashboard,
  IconEmployees,
  IconInventory,
  IconInvoices,
  IconPayments,
  IconReports,
  IconSettings,
  IconSuppliers,
  IconTreasury,
} from "./icons.jsx";

const navItems = [
  { to: "/dashboard", label: "Dashboard", Icon: IconDashboard, end: true },
  { to: "/treasury", label: "Treasury", Icon: IconTreasury },
  { to: "/customers", label: "Customers", Icon: IconCustomers },
  { to: "/suppliers", label: "Suppliers", Icon: IconSuppliers },
  { to: "/invoices", label: "Invoices", Icon: IconInvoices },
  { to: "/payments", label: "Payments", Icon: IconPayments },
  { to: "/inventory", label: "Inventory", Icon: IconInventory },
  { to: "/employees", label: "Employees", Icon: IconEmployees },
  { to: "/reports", label: "Reports", Icon: IconReports },
  { to: "/ai", label: "AI", Icon: IconAI },
  { to: "/settings", label: "Settings", Icon: IconSettings },
  { to: "/admin", label: "Admin", Icon: IconAdmin },
];

const SidebarNav = ({ collapsed, mobileOpen, onClose, onToggleCollapsed }) => {
  const isRtl = typeof document !== "undefined" && document.documentElement?.getAttribute("dir") === "rtl";

  return (
    <aside
      className={`sidebarEnterprise ${collapsed ? "isCollapsed" : ""} ${mobileOpen ? "isMobileOpen" : ""}`.trim()}
    >
      <div className="sidebarBrandRow">
        <div className="sidebarBrand">
          <span className="sidebarBrandMark" aria-hidden="true">
            LIQ
          </span>
          <span className="sidebarBrandName">Ledger IQ</span>
        </div>
        <button type="button" className="iconButton" onClick={onToggleCollapsed} aria-label="Toggle sidebar">
          <span aria-hidden="true">{collapsed ? (isRtl ? "<" : ">") : isRtl ? ">" : "<"}</span>
        </button>
      </div>

      <nav className="sidebarNav" aria-label="Primary navigation">
        {navItems.map(({ to, label, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `navLink ${isActive ? "isActive" : ""}`.trim()}
            onClick={onClose}
            title={collapsed ? label : undefined}
          >
            <span className="navLinkInner">
              <span className="navIconWrap" aria-hidden="true">
                <Icon />
              </span>
              <span className="navLabel">{label}</span>
            </span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
};

export default SidebarNav;
