import React, { useEffect, useState } from "react";

const STORAGE_KEY = "app_mode";
const LIGHT = "light";
const DARK = "dark";

const applyModeClass = (mode) => {
  if (typeof document === "undefined") return;
  document.body.classList.remove(`theme-${LIGHT}`, `theme-${DARK}`);
  document.body.classList.add(`theme-${mode}`);
};

const getInitialMode = () => {
  if (typeof window === "undefined") return LIGHT;
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === LIGHT || stored === DARK) return stored;
  const prefersDark = window.matchMedia?.("(prefers-color-scheme: dark)")?.matches;
  return prefersDark ? DARK : LIGHT;
};

const ModeSwitcher = () => {
  const [mode, setMode] = useState(getInitialMode);

  useEffect(() => {
    applyModeClass(mode);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, mode);
    }
  }, [mode]);

  const toggle = () => {
    setMode((prev) => (prev === LIGHT ? DARK : LIGHT));
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
      aria-label="Toggle light/dark mode"
    >
      {mode === LIGHT ? "Light" : "Dark"}
    </button>
  );
};

export default ModeSwitcher;

// Example:
// <ModeSwitcher />
