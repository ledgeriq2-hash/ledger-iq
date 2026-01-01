import React from "react";
import { NavLink } from "react-router-dom";

const sections = [
  {
    title: "Core",
    items: [
      { to: "/dashboard", label: "Dashboard" },
      { to: "/predictions", label: "Predictions" },
      { to: "/portal", label: "Portal" },
    ],
  },
  {
    title: "Admin",
    items: [{ to: "/settings", label: "Settings" }],
  },
];

const SidebarAdvanced = () => {
  return (
    <aside className="sidebarStatic">
      <div className="sidebarTitle">Ledger IQ</div>
      {sections.map((section) => (
        <div key={section.title} className="sidebarSection">
          <div className="sidebarSectionTitle">{section.title}</div>
          <div className="sidebarSectionItems">
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `sidebarLink ${isActive ? "isActive" : ""}`.trim()}
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </aside>
  );
};

export default SidebarAdvanced;

