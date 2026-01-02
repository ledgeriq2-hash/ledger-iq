import React, { useMemo } from "react";

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const isRtlDoc = () => typeof document !== "undefined" && document.documentElement?.getAttribute("dir") === "rtl";

const asNumber = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};

const pickLabel = (point) => point?.x ?? point?.label ?? point?.month ?? "";

const pickY = (point) => asNumber(point?.y ?? point?.value ?? point?.revenue ?? 0);

const pickLow = (point) => {
  const v = point?.y_low ?? point?.low ?? point?.lower ?? point?.min ?? null;
  return v == null ? null : asNumber(v);
};

const pickHigh = (point) => {
  const v = point?.y_high ?? point?.high ?? point?.upper ?? point?.max ?? null;
  return v == null ? null : asNumber(v);
};

const defaultYFormatter = (v) => {
  try {
    return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(v);
  } catch {
    return String(v);
  }
};

const TimeSeriesChart = ({
  title,
  subtitle,
  actual = [],
  forecast = [],
  intervals = [],
  height = 240,
  yFormatter = defaultYFormatter,
  showGrid = true,
  showHorizon = true,
}) => {
  const rtl = isRtlDoc();
  const width = 720;
  const paddingX = 28;
  const paddingTop = title || subtitle ? 18 : 12;
  const paddingBottom = 28;
  const paddingY = 18;
  const innerW = width - paddingX * 2;
  const innerH = height - (paddingY + paddingBottom + paddingTop);

  const actualPoints = useMemo(
    () => (Array.isArray(actual) ? actual.map((p) => ({ label: pickLabel(p), y: pickY(p) })) : []),
    [actual]
  );

  const forecastPoints = useMemo(
    () =>
      Array.isArray(forecast)
        ? forecast.map((p) => ({ label: pickLabel(p), y: pickY(p) }))
        : [],
    [forecast]
  );

  const bandPoints = useMemo(() => {
    if (!Array.isArray(intervals) || intervals.length === 0) return [];
    return intervals
      .map((p) => ({
        label: pickLabel(p),
        low: pickLow(p),
        high: pickHigh(p),
      }))
      .filter((p) => p.low != null && p.high != null);
  }, [intervals]);

  const labels = useMemo(() => [...actualPoints.map((p) => p.label), ...forecastPoints.map((p) => p.label)], [
    actualPoints,
    forecastPoints,
  ]);

  const allSeries = useMemo(() => [...actualPoints, ...forecastPoints], [actualPoints, forecastPoints]);

  const yDomain = useMemo(() => {
    const values = allSeries.map((p) => p.y);
    let min = values.length ? Math.min(...values) : 0;
    let max = values.length ? Math.max(...values) : 1;
    if (bandPoints.length) {
      min = Math.min(min, ...bandPoints.map((b) => b.low ?? min));
      max = Math.max(max, ...bandPoints.map((b) => b.high ?? max));
    }
    if (min === max) {
      max = min + 1;
    }
    const pad = (max - min) * 0.08;
    return { min: Math.max(0, min - pad), max: max + pad };
  }, [allSeries, bandPoints]);

  const xAt = (i, n) => {
    if (n <= 1) return paddingX + innerW / 2;
    const t = i / (n - 1);
    const pos = rtl ? 1 - t : t;
    return paddingX + pos * innerW;
  };

  const yAt = (v) => {
    const t = (v - yDomain.min) / (yDomain.max - yDomain.min);
    return paddingTop + paddingY + (1 - clamp(t, 0, 1)) * innerH;
  };

  const lineFor = (points, startIndex = 0, total = points.length) =>
    points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${xAt(startIndex + i, total)} ${yAt(p.y)}`)
      .join(" ");

  const totalCount = allSeries.length;
  const actualPath = useMemo(() => (actualPoints.length ? lineFor(actualPoints, 0, totalCount) : ""), [
    actualPoints,
    totalCount,
    yDomain,
    rtl,
  ]);
  const forecastPath = useMemo(
    () => (forecastPoints.length ? lineFor(forecastPoints, actualPoints.length, totalCount) : ""),
    [forecastPoints, actualPoints.length, totalCount, yDomain, rtl]
  );

  const horizonStartX = useMemo(() => {
    if (!showHorizon || forecastPoints.length === 0) return null;
    return xAt(actualPoints.length, totalCount);
  }, [showHorizon, forecastPoints.length, actualPoints.length, totalCount, rtl]);

  const horizonWidth = useMemo(() => {
    if (!showHorizon || forecastPoints.length === 0) return null;
    const endX = xAt(totalCount - 1, totalCount);
    const startX = xAt(actualPoints.length, totalCount);
    return Math.abs(endX - startX);
  }, [showHorizon, forecastPoints.length, actualPoints.length, totalCount, rtl]);

  const bandPath = useMemo(() => {
    if (!bandPoints.length || forecastPoints.length === 0) return "";

    const byLabel = new Map(bandPoints.map((b) => [b.label, b]));
    const points = forecastPoints
      .map((p) => byLabel.get(p.label))
      .filter(Boolean)
      .map((b) => ({ low: b.low, high: b.high }));

    if (points.length !== forecastPoints.length) return "";

    const startIndex = actualPoints.length;
    const upperD = points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${xAt(startIndex + i, totalCount)} ${yAt(p.high)}`)
      .join(" ");
    const lowerD = points
      .map((p, i) => `${xAt(startIndex + (points.length - 1 - i), totalCount)} ${yAt(points[points.length - 1 - i].low)}`)
      .map((xy) => `L ${xy}`)
      .join(" ");

    return `${upperD} ${lowerD} Z`;
  }, [bandPoints, forecastPoints, actualPoints.length, totalCount, yDomain, rtl]);

  const xLabelIdx = useMemo(() => {
    if (labels.length <= 1) return [0];
    const mid = Math.floor(labels.length / 2);
    return [0, mid, labels.length - 1];
  }, [labels.length]);

  const yGrid = useMemo(() => {
    const ticks = [0, 0.5, 1];
    return ticks.map((t) => {
      const v = yDomain.min + (yDomain.max - yDomain.min) * (1 - t);
      return { y: paddingTop + paddingY + t * innerH, value: v };
    });
  }, [yDomain, innerH]);

  return (
    <div className="chartFrame tsChart">
      {title || subtitle ? (
        <div className="chartTitleRow">
          <div>
            {title ? <div className="chartTitle">{title}</div> : null}
            {subtitle ? <div className="chartMeta">{subtitle}</div> : null}
          </div>
          <div className="chartMeta">{totalCount ? `${actualPoints.length} + ${forecastPoints.length}` : "—"}</div>
        </div>
      ) : null}

      <svg className="tsSvg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title || "Time series chart"}>
        {showGrid
          ? yGrid.map((g) => (
              <g key={g.y}>
                <line x1={paddingX} x2={width - paddingX} y1={g.y} y2={g.y} className="tsGridLine" />
                <text x={rtl ? width - paddingX : paddingX} y={g.y - 6} textAnchor={rtl ? "end" : "start"} className="tsYLabel">
                  {yFormatter(g.value)}
                </text>
              </g>
            ))
          : null}

        {showHorizon && horizonStartX != null && horizonWidth != null ? (
          <>
            <rect
              x={Math.min(horizonStartX, horizonStartX + horizonWidth)}
              y={paddingTop + paddingY}
              width={horizonWidth}
              height={innerH}
              className="tsHorizon"
            />
            <line
              x1={horizonStartX}
              x2={horizonStartX}
              y1={paddingTop + paddingY}
              y2={paddingTop + paddingY + innerH}
              className="tsHorizonDivider"
            />
          </>
        ) : null}

        {bandPath ? <path d={bandPath} className="tsBand" /> : null}
        {actualPath ? <path d={actualPath} className="tsLineActual" /> : null}
        {forecastPath ? <path d={forecastPath} className="tsLineForecast" /> : null}

        {xLabelIdx.map((i) => {
          const label = labels[i] || "";
          const x = xAt(i, labels.length);
          const y = height - 8;
          const anchor = rtl ? (i === 0 ? "end" : i === labels.length - 1 ? "start" : "middle") : i === 0 ? "start" : i === labels.length - 1 ? "end" : "middle";
          return (
            <text key={i} x={x} y={y} textAnchor={anchor} className="tsXLabel">
              {label}
            </text>
          );
        })}
      </svg>
    </div>
  );
};

export default TimeSeriesChart;
