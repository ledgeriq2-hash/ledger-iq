import React, { useMemo } from "react";
import { Link, useLocation } from "react-router-dom";
import usePermissions from "../../hooks/usePermissions.js";

const SidebarBasic = ({ mobileOpen = false, onClose }) => {
  const location = useLocation();
  const { hasRole } = usePermissions();

  const navItems = useMemo(() => {
    const base = [
      { to: "/", label: "Dashboard" },
      { to: "/customers", label: "Customers" },
      { to: "/invoices", label: "Invoices" },
      { to: "/recurring-invoices", label: "Recurring" },
      { to: "/inventory", label: "Inventory" },
      { to: "/reports", label: "Reports" },
    ];
    if (hasRole("owner") || hasRole("admin")) {
      base.push(
        { to: "/onboarding", label: "Onboarding" },
        { to: "/billing", label: "Billing" },
        { to: "/admin/tenants", label: "Admin • Tenants" },
        { to: "/admin/feedback", label: "Admin • Feedback" }
      );
    }
    return base;
  }, [hasRole]);

  return (
    <aside
      style={{
        background: "#0f172a",
        color: "#cbd5e1",
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        position: "sticky",
        top: 0,
        height: "100vh",
        boxSizing: "border-box",
        transform: mobileOpen ? "translateX(0)" : "translateX(-110%)",
        transition: "transform 180ms ease",
        maxWidth: "280px",
        width: "80vw",
        zIndex: 9,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div style={{ fontWeight: 700, fontSize: "1.1rem", color: "#e2e8f0" }}>Ledger IQ</div>
        <button
          onClick={onClose}
          aria-label="Close menu"
          style={{
            background: "transparent",
            color: "#e2e8f0",
            border: "none",
            fontSize: "1.2rem",
            cursor: "pointer",
          }}
        >
          ×
        </button>
      </div>
      {navItems.map((item) => {
        const active = location.pathname === item.to;
        return (
          <Link
            key={item.to}
            to={item.to}
            onClick={onClose}
            style={{
              textDecoration: "none",
              color: active ? "#0f172a" : "#cbd5e1",
              background: active ? "#e2e8f0" : "transparent",
              padding: "0.65rem 0.75rem",
              borderRadius: "8px",
              fontWeight: active ? 700 : 500,
              display: "block",
            }}
          >
            {item.label}
          </Link>
        );
      })}
    </aside>
  );
};

export default SidebarBasic;
