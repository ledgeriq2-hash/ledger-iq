import React, { useMemo } from "react";
import { NavLink } from "react-router-dom";
import usePermissions from "../../hooks/usePermissions.js";

const SidebarBasic = ({ mobileOpen = false, onClose }) => {
  const { hasRole } = usePermissions();

  const navItems = useMemo(() => {
    const base = [
      { to: "/dashboard", label: "Dashboard" },
      { to: "/predictions", label: "Predictions" },
      { to: "/portal", label: "Portal" },
    ];

    if (hasRole("owner") || hasRole("admin")) {
      base.push({ to: "/settings", label: "Settings" });
    }

    return base;
  }, [hasRole]);

  return (
    <aside className={`sidebar ${mobileOpen ? "isOpen" : ""}`.trim()}>
      <div className="sidebarHeader">
        <div className="sidebarTitle">Ledger IQ</div>
        <button onClick={onClose} aria-label="Close menu" className="iconButton" type="button">
          ?
        </button>
      </div>
      {navItems.map((item) => {
        return (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onClose}
            className={({ isActive }) => `sidebarLink ${isActive ? "isActive" : ""}`.trim()}
          >
            {item.label}
          </NavLink>
        );
      })}
    </aside>
  );
};

export default SidebarBasic;
