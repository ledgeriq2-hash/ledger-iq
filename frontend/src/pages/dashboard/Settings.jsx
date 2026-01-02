import React, { useMemo, useState } from "react";

import { useSettings, useUpdateSettings } from "../../hooks/useSettings.js";
import Button from "../../components/kit/Button.jsx";
import Card from "../../components/kit/Card.jsx";
import Skeleton from "../../components/kit/Skeleton.jsx";
import StatusPill from "../../components/kit/StatusPill.jsx";

const TABS = ["Feature Toggles", "Customization", "Permissions"];

const getToggle = (settings, key) => {
  const ft = settings?.feature_toggles || {};
  const pages = ft?.pages || {};
  if (Object.prototype.hasOwnProperty.call(pages, key)) return Boolean(pages[key]);
  if (Object.prototype.hasOwnProperty.call(ft, key)) return Boolean(ft[key]);
  return true;
};

const setToggle = (draft, key, enabled) => {
  const ft = { ...(draft.feature_toggles || {}) };
  const pages = { ...(ft.pages || {}) };

  if (key.startsWith("dashboard_")) {
    pages[key] = Boolean(enabled);
    ft.pages = pages;
  } else {
    ft[key] = Boolean(enabled);
  }

  return { ...draft, feature_toggles: ft };
};

const Settings = () => {
  const settingsQuery = useSettings();
  const updateSettings = useUpdateSettings();

  const [tab, setTab] = useState(TABS[0]);

  const settings = settingsQuery.data;
  const draft = useMemo(() => settings || {}, [settings]);
  const [localDraft, setLocalDraft] = useState(null);

  const effective = localDraft || draft;

  const save = async () => {
    await updateSettings.mutateAsync(effective);
    setLocalDraft(null);
  };

  const onToggle = (key) => (e) => {
    const next = setToggle(effective, key, e.target.checked);
    setLocalDraft(next);
  };

  if (settingsQuery.isLoading) {
    return (
      <Card title="Settings">
        <div className="portalGrid">
          <Skeleton className="kit-skeletonLg" />
          <Skeleton className="kit-skeletonLg" />
        </div>
      </Card>
    );
  }

  if (settingsQuery.error) {
    return (
      <Card title="Settings">
        <StatusPill tone="danger">{settingsQuery.error?.message || "Failed to load settings"}</StatusPill>
      </Card>
    );
  }

  return (
    <div className="portalGrid">
      <Card
        title="Settings"
        headerRight={
          <div className="kit-inline">
            <StatusPill tone="info">Applies immediately</StatusPill>
            <Button type="button" disabled={!localDraft || updateSettings.isPending} onClick={save}>
              {updateSettings.isPending ? "Saving..." : "Save"}
            </Button>
          </div>
        }
      >
        {updateSettings.error ? (
          <StatusPill tone="danger">{updateSettings.error?.message || "Failed to save settings"}</StatusPill>
        ) : null}

        <div className="settingsTabs">
          {TABS.map((t) => (
            <Button key={t} type="button" variant={tab === t ? "primary" : "ghost"} onClick={() => setTab(t)}>
              {t}
            </Button>
          ))}
        </div>
      </Card>

      {tab === "Feature Toggles" ? (
        <Card title="Feature Toggles">
          <div className="settingsList">
            <label className="toggleRow">
              <input className="toggleInput" type="checkbox" checked={getToggle(effective, "ai")} onChange={onToggle("ai")} />
              <span className="toggleText">AI</span>
            </label>
            <label className="toggleRow">
              <input className="toggleInput" type="checkbox" checked={getToggle(effective, "suppliers")} onChange={onToggle("suppliers")} />
              <span className="toggleText">Suppliers</span>
            </label>
            <label className="toggleRow">
              <input className="toggleInput" type="checkbox" checked={getToggle(effective, "workers")} onChange={onToggle("workers")} />
              <span className="toggleText">Workers</span>
            </label>
            <label className="toggleRow">
              <input className="toggleInput" type="checkbox" checked={getToggle(effective, "debts")} onChange={onToggle("debts")} />
              <span className="toggleText">Debts</span>
            </label>
            <label className="toggleRow">
              <input className="toggleInput" type="checkbox" checked={getToggle(effective, "invoices")} onChange={onToggle("invoices")} />
              <span className="toggleText">Invoices</span>
            </label>
            <div className="kit-muted">Page-level toggles</div>
            <label className="toggleRow">
              <input className="toggleInput" type="checkbox" checked={getToggle(effective, "dashboard_ai")} onChange={onToggle("dashboard_ai")} />
              <span className="toggleText">Dashboard / AI</span>
            </label>
            <label className="toggleRow">
              <input className="toggleInput" type="checkbox" checked={getToggle(effective, "dashboard_suppliers")} onChange={onToggle("dashboard_suppliers")} />
              <span className="toggleText">Dashboard / Suppliers</span>
            </label>
            <label className="toggleRow">
              <input className="toggleInput" type="checkbox" checked={getToggle(effective, "dashboard_workers")} onChange={onToggle("dashboard_workers")} />
              <span className="toggleText">Dashboard / Workers</span>
            </label>
            <label className="toggleRow">
              <input className="toggleInput" type="checkbox" checked={getToggle(effective, "dashboard_debts")} onChange={onToggle("dashboard_debts")} />
              <span className="toggleText">Dashboard / Debts</span>
            </label>
            <label className="toggleRow">
              <input className="toggleInput" type="checkbox" checked={getToggle(effective, "dashboard_invoices")} onChange={onToggle("dashboard_invoices")} />
              <span className="toggleText">Dashboard / Invoices</span>
            </label>
          </div>
        </Card>
      ) : null}

      {tab === "Customization" ? (
        <Card title="Customization">
          <div className="portalGrid">
            <StatusPill tone="info">Palette locked</StatusPill>
            <div className="kit-muted">Currency, taxes, field labels, and theme are persisted; UI wiring is incremental.</div>
          </div>
        </Card>
      ) : null}

      {tab === "Permissions" ? (
        <Card title="Permissions">
          <div className="portalGrid">
            <StatusPill tone="info">Placeholder</StatusPill>
            <div className="kit-muted">RBAC configuration will be implemented after bounded contexts stabilize.</div>
          </div>
        </Card>
      ) : null}
    </div>
  );
};

export default Settings;

