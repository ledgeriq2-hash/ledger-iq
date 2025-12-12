import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "../assets/locales/en.json";
import ar from "../assets/locales/ar.json";

const resources = {
  en: { translation: en },
  ar: { translation: ar },
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: "en",
    fallbackLng: "en",
    supportedLngs: ["en", "ar"],
    interpolation: {
      escapeValue: false, // React already escapes by default
    },
    returnObjects: true,
  });

export default i18n;
