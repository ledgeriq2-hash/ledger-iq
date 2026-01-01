import React, { useEffect, useMemo, useState } from "react";
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
  const tResult = useTranslation();
  const i18n = tResult?.i18n;

  const safeGetLang = useMemo(() => {
    const lang =
      (typeof window !== "undefined" && localStorage.getItem(STORAGE_KEY)) ||
      i18n?.language ||
      "en";
    return lang === "ar" ? "ar" : "en";
  }, [i18n?.language]);

  const [current, setCurrent] = useState(safeGetLang);
  const canChangeLanguage = typeof i18n?.changeLanguage === "function";

  useEffect(() => {
    applyDirection(current);
    if (canChangeLanguage) {
      i18n.changeLanguage(current);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (lang) => {
    const next = lang === "ar" ? "ar" : "en";
    setCurrent(next);
    applyDirection(next);

    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, next);
    }

    if (canChangeLanguage) {
      i18n.changeLanguage(next);
    }
  };

  return (
    <div className="langSwitcher">
      <button
        type="button"
        onClick={() => handleChange("en")}
        className={`langButton ${current === "en" ? "langButtonActive" : ""}`.trim()}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => handleChange("ar")}
        className={`langButton ${current === "ar" ? "langButtonActive" : ""}`.trim()}
      >
        AR
      </button>
    </div>
  );
};

export default LanguageSwitcher;
