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
  const { tenantId, tenantOptions, tenantOptionsLoading, bootstrapDemoTenant } = useAuth();
  const [bootstrapping, setBootstrapping] = useState(false);
  const [bootstrapError, setBootstrapError] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  useEffect(() => {
    if (tenantId || tenantOptionsLoading) return;
    if (Array.isArray(tenantOptions) && tenantOptions.length > 1) {
      const input = document.querySelector(".tenantSelectorInput");
      if (input) input.focus();
    }
  }, [tenantId, tenantOptions, tenantOptionsLoading]);

  const handleBootstrap = async () => {
    setBootstrapping(true);
    setBootstrapError("");
    try {
      await bootstrapDemoTenant();
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        err?.response?.data?.error?.message ||
        err?.message ||
        "Failed to bootstrap tenant.";
      setBootstrapError(String(message));
    } finally {
      setBootstrapping(false);
    }
  };

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
          ) : tenantOptionsLoading ? (
            <EmptyState
              title="Loading companies"
              message="Fetching accessible tenants..."
              compact
            />
          ) : Array.isArray(tenantOptions) && tenantOptions.length === 0 ? (
            <div className="u-grid u-gap-2">
              <EmptyState
                title="No companies yet"
                message={
                  bootstrapError ||
                  "Create a demo company to start exploring Ledger IQ."
                }
                actionLabel={bootstrapping ? "Creating..." : "Create demo company"}
                onAction={handleBootstrap}
              />
            </div>
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
