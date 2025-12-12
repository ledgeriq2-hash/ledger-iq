import React from "react";
import Card from "../ui/Card.jsx";
import Tag from "../ui/Tag.jsx";

const RevenueForecastChart = ({ data }) => {
  const points = data?.forecast || [10, 12, 13, 15];
  const baseline = data?.baseline || [8, 9, 10];

  return (
    <Card title="Revenue Forecast" actions={<Tag tone="success">AI</Tag>} style={{ minHeight: "240px" }}>
      <div
        style={{
          height: "180px",
          background: "linear-gradient(135deg, #e0f2fe, #ecfeff)",
          borderRadius: "12px",
          display: "flex",
          alignItems: "flex-end",
          gap: "8px",
          padding: "12px",
        }}
      >
        {[...baseline, ...points].map((value, idx) => (
          <div
            key={idx}
            style={{
              height: `${20 + value * 5}px`,
              width: "10px",
              background: idx < baseline.length ? "#0ea5e9" : "#22c55e",
              borderRadius: "6px 6px 0 0",
            }}
          />
        ))}
      </div>
    </Card>
  );
};

export default RevenueForecastChart;
