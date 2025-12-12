import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import httpClient from "../../api/httpClient";
import LoadingSpinner from "../../components/common/LoadingSpinner.jsx";

const Profile = () => {
  const { t } = useTranslation();
  const [form, setForm] = useState({
    name: "",
    email: "",
    preferred_language: "en",
    preferred_theme: "gold",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await httpClient.get("/me/profile");
        const data = res.data || {};
        setForm({
          name: data.name || data.full_name || "",
          email: data.email || "",
          preferred_language: data.preferred_language || "en",
          preferred_theme: data.preferred_theme || "gold",
        });
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      await httpClient.patch("/me/profile", form);
      setSuccess(true);
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message={t("status.loading", { defaultValue: "Loading profile..." })} />;
  }

  if (error) {
    return (
      <div style={{ padding: "1rem" }}>
        <p style={{ color: "#b91c1c" }}>{t("status.error", { defaultValue: "Failed to load profile." })}</p>
        <pre style={{ background: "#fef2f2", padding: "0.75rem", borderRadius: "8px", overflow: "auto" }}>
          {error?.message}
        </pre>
      </div>
    );
  }

  return (
    <div style={{ padding: "1rem", maxWidth: "640px" }}>
      <h1 style={{ marginTop: 0 }}>{t("nav.profile", { defaultValue: "Profile" })}</h1>
      <form onSubmit={handleSubmit} className="card" style={{ display: "grid", gap: "1rem" }}>
        <div style={{ display: "grid", gap: "0.35rem" }}>
          <label htmlFor="name">{t("profile.name", { defaultValue: "Name" })}</label>
          <input
            id="name"
            name="name"
            value={form.name}
            onChange={handleChange}
            style={{ padding: "0.6rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}
          />
        </div>
        <div style={{ display: "grid", gap: "0.35rem" }}>
          <label htmlFor="email">{t("profile.email", { defaultValue: "Email" })}</label>
          <input
            id="email"
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
            style={{ padding: "0.6rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}
          />
        </div>
        <div style={{ display: "grid", gap: "0.35rem" }}>
          <label htmlFor="preferred_language">
            {t("profile.language", { defaultValue: "Preferred language" })}
          </label>
          <select
            id="preferred_language"
            name="preferred_language"
            value={form.preferred_language}
            onChange={handleChange}
            style={{ padding: "0.6rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}
          >
            <option value="en">English</option>
            <option value="ar">Arabic</option>
          </select>
        </div>
        <div style={{ display: "grid", gap: "0.35rem" }}>
          <label htmlFor="preferred_theme">
            {t("profile.theme", { defaultValue: "Preferred theme" })}
          </label>
          <select
            id="preferred_theme"
            name="preferred_theme"
            value={form.preferred_theme}
            onChange={handleChange}
            style={{ padding: "0.6rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}
          >
            <option value="gold">Gold</option>
            <option value="silver">Silver</option>
          </select>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <button
            className="btn btn-primary"
            type="submit"
            disabled={saving}
            style={{ minWidth: "120px" }}
          >
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

export default Profile;
