import React, { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api from "../../../utils/api";

const CustomerSettings = () => {
  const { t } = useTranslation();
  const { portalData, token } = useOutletContext();
  const [settings, setSettings] = useState({ notifications: true, language: "en" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (portalData?.settings) {
      setSettings({
        notifications: portalData.settings.notifications ?? true,
        language: portalData.settings.language || "en",
      });
    }
  }, [portalData?.settings]);

  const handleChange = (e) => {
    const { name, type, checked, value } = e.target;
    setSettings((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!token) return;
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      await api.patch(`/portal/customer/${token}/settings`, settings);
      setSuccess(true);
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  };

  if (!portalData) {
    return <div>{t("status.loading", { defaultValue: "Loading..." })}</div>;
  }

  return (
    <div style={{ display: "grid", gap: "1rem", maxWidth: "520px" }}>
      <h2 style={{ marginTop: 0 }}>{t("nav.settings", { defaultValue: "Settings" })}</h2>
      {error && <div style={{ color: "#b91c1c" }}>{t("status.error", { defaultValue: "Failed to load settings." })}</div>}
      <form onSubmit={handleSave} className="card" style={{ display: "grid", gap: "0.75rem" }}>
        <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input
            type="checkbox"
            name="notifications"
            checked={settings.notifications}
            onChange={handleChange}
          />
          {t("notifications.title", { defaultValue: "Notifications" })}
        </label>

        <div style={{ display: "grid", gap: "0.35rem" }}>
          <label htmlFor="language">{t("profile.language", { defaultValue: "Preferred language" })}</label>
          <select
            id="language"
            name="language"
            value={settings.language}
            onChange={handleChange}
            style={{ padding: "0.6rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}
          >
            <option value="en">English</option>
            <option value="ar">Arabic</option>
          </select>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button className="btn btn-primary" type="submit" disabled={saving}>
            {saving
              ? t("status.loading", { defaultValue: "Saving..." })
              : t("actions.save", { defaultValue: "Save" })}
          </button>
          {success && <span style={{ color: "#16a34a" }}>{t("status.success", { defaultValue: "Saved" })}</span>}
        </div>
      </form>
    </div>
  );
};

export default CustomerSettings;
