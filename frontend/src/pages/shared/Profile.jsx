import React, { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../../api/generated/index.js";
import LoadingSpinner from "../../components/common/LoadingSpinner.jsx";
import Card from "../../components/ui/Card.jsx";
import Input from "../../components/ui/Input.jsx";
import Select from "../../components/ui/Select.jsx";
import ErrorState from "../../components/ui/ErrorState.jsx";
import Button from "../../components/ui/Button.jsx";

const Profile = () => {
  const { t } = useTranslation();
  const [form, setForm] = useState({
    name: "",
    email: "",
    preferred_language: "en",
    preferred_theme: "dark",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const storedLanguage =
        typeof window !== "undefined" ? localStorage.getItem("preferred_language") || "en" : "en";
      const storedTheme =
        typeof window !== "undefined" ? localStorage.getItem("preferred_theme") || "dark" : "dark";
      const res = await api.auth.me();
      const data = res?.user || res || {};
      setForm({
        name: data.name || data.full_name || "",
        email: data.email || "",
        preferred_language: data.preferred_language || storedLanguage,
        preferred_theme: data.preferred_theme || storedTheme,
      });
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

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
      if (typeof window !== "undefined") {
        localStorage.setItem("preferred_language", form.preferred_language);
        localStorage.setItem("preferred_theme", form.preferred_theme);
      }
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
      <div className="u-pad-4">
        <ErrorState
          title={t("status.error", { defaultValue: "Failed to load profile." })}
          error={error}
          onRetry={loadProfile}
        />
      </div>
    );
  }

  return (
    <div className="u-pad-4 u-maxw-sm u-grid u-gap-4">
      <h1 className="u-m-0">{t("nav.profile", { defaultValue: "Profile" })}</h1>
      <Card title={t("nav.profile", { defaultValue: "Profile" })} className="profileCard">
        <form onSubmit={handleSubmit} className="formStack">
          <Input
            label={t("profile.name", { defaultValue: "Name" })}
            name="name"
            value={form.name}
            onChange={handleChange}
          />
          <Input
            label={t("profile.email", { defaultValue: "Email" })}
            type="email"
            name="email"
            value={form.email}
            onChange={handleChange}
          />
          <Select
            label={t("profile.language", { defaultValue: "Preferred language" })}
            name="preferred_language"
            value={form.preferred_language}
            onChange={handleChange}
            options={[
              { label: "English", value: "en" },
              { label: "Arabic", value: "ar" },
            ]}
          />
          <Select
            label={t("profile.theme", { defaultValue: "Appearance" })}
            name="preferred_theme"
            value={form.preferred_theme}
            onChange={handleChange}
            options={[
              { label: "Light", value: "light" },
              { label: "Dark", value: "dark" },
            ]}
          />

          <div className="u-flex u-gap-3 u-items-center u-wrap">
            <Button type="submit" disabled={saving} className="profileSave">
              {saving ? t("status.loading", { defaultValue: "Saving..." }) : t("actions.save", { defaultValue: "Save" })}
            </Button>
            {success && <span className="formHelper">{t("status.success", { defaultValue: "Saved" })}</span>}
          </div>
        </form>
      </Card>
    </div>
  );
};

export default Profile;
