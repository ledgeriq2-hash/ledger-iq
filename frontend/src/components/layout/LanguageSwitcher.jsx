import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

const STORAGE_KEY = "app_language";

const applyDirection = (lang) => {
  if (typeof document === "undefined") return;
  const isArabic = lang === "ar";
  const dir = isArabic ? "rtl" : "ltr";
  document.documentElement.setAttribute("dir", dir);
  document.documentElement.setAttribute("lang", lang);
};

const LanguageSwitcher = () => {
  const { i18n } = useTranslation();
  const [current, setCurrent] = useState(() => {
    if (typeof window === "undefined") return i18n.language || "en";
    return localStorage.getItem(STORAGE_KEY) || i18n.language || "en";
  });

  useEffect(() => {
    const initialLang = current;
    i18n.changeLanguage(initialLang);
    applyDirection(initialLang);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleChange = (lang) => {
    setCurrent(lang);
    i18n.changeLanguage(lang);
    applyDirection(lang);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, lang);
    }
  };

  return (
    <div style={{ display: "inline-flex", gap: "0.5rem", alignItems: "center" }}>
      <button
        type="button"
        onClick={() => handleChange("en")}
        style={{
          padding: "0.35rem 0.65rem",
          borderRadius: "0.5rem",
          border: current === "en" ? "1px solid #2563eb" : "1px solid #e2e8f0",
          background: current === "en" ? "#eff6ff" : "#fff",
          cursor: "pointer",
        }}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => handleChange("ar")}
        style={{
          padding: "0.35rem 0.65rem",
          borderRadius: "0.5rem",
          border: current === "ar" ? "1px solid #2563eb" : "1px solid #e2e8f0",
          background: current === "ar" ? "#eff6ff" : "#fff",
          cursor: "pointer",
        }}
      >
        AR
      </button>
    </div>
  );
};

export default LanguageSwitcher;

// Example:
// <LanguageSwitcher />
