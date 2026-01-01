import React from "react";
import Card from "../ui/Card.jsx";
import EmptyState from "../ui/EmptyState.jsx";
import Tag from "../ui/Tag.jsx";

const AnomalyTimelineChart = ({ data }) => {
  const anomalies = Array.isArray(data?.anomalies)
    ? data.anomalies
    : Array.isArray(data?.items)
      ? data.items
      : Array.isArray(data)
        ? data
        : [];

  const toneForSeverity = (value) => {
    const severity = String(value || "").toLowerCase();
    if (severity.includes("high") || severity.includes("critical")) return "danger";
    if (severity.includes("medium")) return "warning";
    return "default";
  };

  return (
    <Card title="Anomaly Timeline" actions={<Tag tone="warning">Monitoring</Tag>} className="chartCard chartCardSm">
      <div className="anomalyWrap">
        {anomalies.length === 0 ? (
          <EmptyState compact title="No anomalies detected" message="AI insights will appear after the next run." />
        ) : (
          anomalies.map((a, idx) => (
            <div key={a.id || idx} className="anomalyPill">
              <div className="u-flex u-gap-2 u-items-center">
                <Tag tone={toneForSeverity(a.severity)}>{a.severity || "info"}</Tag>
                <span>{a.title || a.message || "Anomaly insight"}</span>
              </div>
              <div className="u-text-muted">{a.created_at || a.timestamp || "?"}</div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
};

export default AnomalyTimelineChart;
