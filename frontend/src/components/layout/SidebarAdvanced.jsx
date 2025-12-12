import React from "react";
import { Link, useLocation } from "react-router-dom";

const sections = [
  {
    title: "Core",
    items: [
      { to: "/", label: "Dashboard" },
      { to: "/customers", label: "Customers" },
      { to: "/invoices", label: "Invoices" },
      { to: "/payments", label: "Payments" },
      { to: "/expenses", label: "Expenses" },
    ],
  },
  {
    title: "Insights",
    items: [
      { to: "/reports", label: "Reports" },
      { to: "/ai", label: "AI Insights" },
    ],
  },
];

const SidebarAdvanced = () => {
  const location = useLocation();

  return (
    <aside
      style={{
        background: "#0b1221",
        color: "#cbd5e1",
        width: "240px",
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
      }}
    >
      <div style={{ fontWeight: 700, fontSize: "1.1rem", color: "#e2e8f0" }}>Ledger IQ</div>
      {sections.map((section) => (
        <div key={section.title}>
          <div style={{ fontSize: "0.85rem", textTransform: "uppercase", color: "#94a3b8", marginBottom: "0.5rem" }}>
            {section.title}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
            {section.items.map((item) => {
              const active = location.pathname === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  style={{
                    textDecoration: "none",
                    color: active ? "#0b1221" : "#cbd5e1",
                    background: active ? "#e2e8f0" : "transparent",
                    padding: "0.6rem 0.75rem",
                    borderRadius: "10px",
                    fontWeight: active ? 700 : 500,
                  }}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </aside>
  );
};

export default SidebarAdvanced;
