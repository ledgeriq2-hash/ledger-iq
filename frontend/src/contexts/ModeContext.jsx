import React, { createContext, useMemo, useState } from "react";

export const ModeContext = createContext({
  mode: "light",
  toggleMode: () => {},
});

export const ModeProvider = ({ children }) => {
  const [mode, setMode] = useState("light");

  const toggleMode = () => setMode((prev) => (prev === "light" ? "dark" : "light"));

  const value = useMemo(() => ({ mode, toggleMode }), [mode]);

  return <ModeContext.Provider value={value}>{children}</ModeContext.Provider>;
};
