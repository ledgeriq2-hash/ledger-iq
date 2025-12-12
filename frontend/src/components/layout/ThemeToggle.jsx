import React, { useEffect, useState } from "react";
import "../../assets/themes/gold.css";
import "../../assets/themes/silver.css";

const STORAGE_KEY = "app_color_theme";
const GOLD = "gold";
const SILVER = "silver";

const applyTheme = (theme) => {
  if (typeof document === "undefined") return;
  document.body.setAttribute("data-color-theme", theme);
};

const getInitialTheme = () => {
  if (typeof window === "undefined") return GOLD;
  const stored = localStorage.getItem(STORAGE_KEY);
  return stored === SILVER ? SILVER : GOLD;
};

const ThemeToggle = () => {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, theme);
    }
  }, [theme]);

  const toggle = () => {
    setTheme((prev) => (prev === GOLD ? SILVER : GOLD));
  };

  return (
    <button
      type="button"
      onClick={toggle}
      style={{
        padding: "0.35rem 0.75rem",
        borderRadius: "0.5rem",
        border: "1px solid #e2e8f0",
        background: "#fff",
        cursor: "pointer",
      }}
      aria-label="Toggle theme variant"
    >
      {theme === GOLD ? "Gold" : "Silver"}
    </button>
  );
};

export default ThemeToggle;

// Example:
// <ThemeToggle />
