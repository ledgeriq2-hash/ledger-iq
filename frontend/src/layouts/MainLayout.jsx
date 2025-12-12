import React, { useState } from "react";
import Header from "../components/layout/Header.jsx";
import SidebarBasic from "../components/layout/SidebarBasic.jsx";

const MainLayout = ({ children }) => {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "240px 1fr",
        minHeight: "100vh",
        background: "#f8fafc",
      }}
    >
      <div
        style={{
          position: "fixed",
          inset: 0,
          background: mobileOpen ? "rgba(15,23,42,0.45)" : "transparent",
          pointerEvents: mobileOpen ? "auto" : "none",
          transition: "background 150ms ease",
          zIndex: 8,
        }}
        onClick={() => setMobileOpen(false)}
      />
      <SidebarBasic mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div style={{ display: "flex", flexDirection: "column" }}>
        <Header onMenu={() => setMobileOpen(true)} />
        <main style={{ padding: "1.5rem", width: "100%", boxSizing: "border-box" }}>{children}</main>
      </div>
    </div>
  );
};

export default MainLayout;
