import React from "react";
import Card from "../ui/Card.jsx";
import EmptyState from "../ui/EmptyState.jsx";

const CashflowChart = ({ data }) => {
  const values = Array.isArray(data)
    ? data.map((value) => (Number.isFinite(Number(value)) ? Number(value) : 0))
    : Array.isArray(data?.series?.values)
      ? data.series.values.map((value) => (Number.isFinite(Number(value)) ? Number(value) : 0))
      : [];
  const max = Math.max(...values, 1);
  const width = 320;
  const height = 160;
  const gap = 10;
  const barWidth = Math.max(8, Math.floor((width - gap * (values.length - 1)) / values.length));

  return (
    <Card title="Cashflow" className="chartCard chartCardSm">
      {!values.length ? (
        <EmptyState compact title="No cashflow data" message="Import transactions to populate the chart." />
      ) : (
        <svg className="chartSvg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Cashflow chart">
          {values.map((value, idx) => {
            const x = idx * (barWidth + gap);
            const h = Math.round((value / max) * (height - 8));
            const y = height - h;
            return <rect key={idx} x={x} y={y} width={barWidth} height={h} rx={8} fill="var(--color-primary)" />;
          })}
        </svg>
      )}
    </Card>
  );
};

export default CashflowChart;
