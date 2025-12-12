import React from "react";
import Card from "../ui/Card.jsx";

const CashflowChart = ({ data }) => {
  const values = data || [20, 15, 10, 25, 18];
  const max = Math.max(...values, 1);

  return (
    <Card title="Cashflow" style={{ minHeight: "220px" }}>
      <div style={{ display: "flex", gap: "10px", alignItems: "flex-end", height: "160px" }}>
        {values.map((value, idx) => (
          <div
            key={idx}
            style={{
              height: `${(value / max) * 100}%`,
              width: "12px",
              background: "#6366f1",
              borderRadius: "8px 8px 0 0",
            }}
          />
        ))}
      </div>
    </Card>
  );
};

export default CashflowChart;
