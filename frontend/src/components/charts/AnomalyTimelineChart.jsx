import React from "react";
import Card from "../ui/Card.jsx";
import Tag from "../ui/Tag.jsx";

const AnomalyTimelineChart = ({ data }) => {
  const anomalies = data?.anomalies || [];
  return (
    <Card title="Anomaly Timeline" actions={<Tag tone="warning">Monitoring</Tag>} style={{ minHeight: "200px" }}>
      <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
        {anomalies.length === 0 && <span style={{ color: "#94a3b8" }}>No anomalies detected</span>}
        {anomalies.map((a, idx) => (
          <div
            key={idx}
            style={{
              padding: "0.45rem 0.6rem",
              borderRadius: "10px",
              background: "rgba(239,68,68,0.1)",
              color: "#991b1b",
              border: "1px solid rgba(239,68,68,0.25)",
              fontSize: "0.9rem",
            }}
          >
            #{a.index} • {a.value}
          </div>
        ))}
      </div>
    </Card>
  );
};

export default AnomalyTimelineChart;
