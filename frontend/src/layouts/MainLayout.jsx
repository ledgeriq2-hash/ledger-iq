import React, { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";

import SidebarNav from "../components/layout/SidebarNav.jsx";
import Topbar from "../components/layout/Topbar.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import useAuth from "../hooks/useAuth.js";

const COLLAPSE_KEY = "layout_sidebar_collapsed";

const readCollapsed = () => {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(COLLAPSE_KEY) === "1";
};

const MainLayout = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const { tenantId } = useAuth();

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  return (
    <div className={`layoutShell ${mobileOpen ? "isMobileOpen" : ""}`.trim()}>
      <div className={`layoutOverlay ${mobileOpen ? "isOpen" : ""}`.trim()} onClick={() => setMobileOpen(false)} />
      <SidebarNav
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onClose={() => setMobileOpen(false)}
        onToggleCollapsed={() => setCollapsed((v) => !v)}
      />
      <div className="layoutMain">
        <Topbar onMobileMenu={() => setMobileOpen(true)} sidebarCollapsed={collapsed} />
        <main className="layoutContent">
          {tenantId ? (
            children ?? <Outlet />
          ) : (
            <EmptyState
              title="Select a company to continue"
              message="Treasury stays the single source of truth once a tenant is selected."
              actionLabel="Focus tenant selector"
              onAction={() => {
                const input = document.querySelector(".tenantSelectorInput");
                if (input) input.focus();
              }}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
