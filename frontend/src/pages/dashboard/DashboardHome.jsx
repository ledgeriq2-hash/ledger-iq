import React from "react";
import { Link } from "react-router-dom";

import { useAiSummary } from "../../hooks/useAIInsights.js";
import { useSettings } from "../../hooks/useSettings.js";
import Card from "../../components/kit/Card.jsx";
import Button from "../../components/kit/Button.jsx";
import Skeleton from "../../components/kit/Skeleton.jsx";
import StatusPill from "../../components/kit/StatusPill.jsx";

const isEnabled = (settings, key) => {
  const ft = settings?.feature_toggles || {};
  const pages = ft?.pages || {};
  if (Object.prototype.hasOwnProperty.call(pages, key)) return Boolean(pages[key]);
  if (Object.prototype.hasOwnProperty.call(ft, key)) return Boolean(ft[key]);
  return true;
};

const DashboardHome = () => {
  const settingsQuery = useSettings();
  const settings = settingsQuery.data;
  const showAi = isEnabled(settings, "ai") && isEnabled(settings, "dashboard_ai");
  const { data, isLoading, error } = useAiSummary({ enabled: showAi });
  const insights = Array.isArray(data?.insights) ? data.insights : [];

  return (
    <div className="portalGrid">
      <Card title="Environment">
        <div className="portalGrid">
          <StatusPill tone="info">Dev headers required</StatusPill>
          <div>Set `VITE_TENANT_ID` (required) and `VITE_ACTOR_ID` (optional).</div>
        </div>
      </Card>
      {showAi ? (
        <Card
          title="AI Insights"
          headerRight={
            <Link to="/dashboard/ai">
              <Button variant="ghost" type="button">
                View all
              </Button>
            </Link>
          }
        >
          {isLoading ? (
            <div className="portalGrid">
              <Skeleton className="kit-skeletonLg" />
              <Skeleton className="kit-skeletonLg" />
              <Skeleton className="kit-skeletonLg" />
            </div>
          ) : error ? (
            <StatusPill tone="danger">{error?.message || "Failed to load AI summary"}</StatusPill>
          ) : insights.length === 0 ? (
            <StatusPill tone="info">No insights yet</StatusPill>
          ) : (
            <div className="portalGrid">
              {insights.slice(0, 3).map((i) => (
                <div key={i.id} className="kit-kvItem">
                  <div className="kit-inline">
                    <StatusPill
                      tone={
                        String(i.severity || "").toLowerCase() === "danger"
                          ? "danger"
                          : String(i.severity || "").toLowerCase() === "warning"
                          ? "warning"
                          : "info"
                      }
                    >
                      {i.severity}
                    </StatusPill>
                    <StatusPill tone="info">{Math.round(Number(i.confidence || 0) * 100)}%</StatusPill>
                  </div>
                  <div className="kit-cardTitle">{i.title}</div>
                  <div className="kit-muted">{i.message}</div>
                </div>
              ))}
            </div>
          )}
        </Card>
      ) : null}
      <Card title="Roadmap">
        <div className="portalGrid">
          <StatusPill tone="success">No auth</StatusPill>
          <div>Financial writes are routed through backend use cases.</div>
        </div>
      </Card>
    </div>
  );
};

export default DashboardHome;
