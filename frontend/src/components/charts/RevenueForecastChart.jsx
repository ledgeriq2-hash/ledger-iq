import React from "react";
import Card from "../ui/Card.jsx";
import EmptyState from "../ui/EmptyState.jsx";
import Tag from "../ui/Tag.jsx";

const RevenueForecastChart = ({ data }) => {
  const toNumber = (value) => {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  };

  const baseline = Array.isArray(data?.baseline) ? data.baseline.map(toNumber) : [];
  const forecast = Array.isArray(data?.forecast) ? data.forecast.map(toNumber) : [];
  const seriesValues = Array.isArray(data?.values)
    ? data.values.map(toNumber)
    : Array.isArray(data?.series?.values)
      ? data.series.values.map(toNumber)
      : [];
  const values = baseline.length || forecast.length ? [...baseline, ...forecast] : seriesValues;
  const max = Math.max(...values, 1);
  const width = 360;
  const height = 180;
  const gap = 8;
  const barWidth = Math.max(8, Math.floor((width - gap * (values.length - 1)) / values.length));

  return (
    <Card title="Revenue Forecast" actions={<Tag tone="success">AI</Tag>} className="chartCard chartCardMd">
      {!values.length ? (
        <EmptyState
          compact
          title="No forecast data"
          message="Connect the forecasting service to view revenue projections."
        />
      ) : (
        <div className="chartFrame">
          <svg className="chartSvg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Revenue forecast chart">
            {values.map((value, idx) => {
              const x = idx * (barWidth + gap);
              const h = Math.round((value / max) * (height - 10));
              const y = height - h;
              const isBaseline = baseline.length ? idx < baseline.length : false;
              return (
                <rect
                  key={idx}
                  x={x}
                  y={y}
                  width={barWidth}
                  height={h}
                  rx={6}
                  fill={isBaseline ? "var(--color-border)" : "var(--color-primary)"}
                />
              );
            })}
          </svg>
        </div>
      )}
    </Card>
  );
};

export default RevenueForecastChart;
