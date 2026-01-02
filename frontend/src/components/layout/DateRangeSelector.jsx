import React, { useContext, useMemo } from "react";

import { DateRangeContext } from "../../contexts/DateRangeContext.jsx";

const presets = [
  { value: "last_7_days", label: "Last 7 days" },
  { value: "last_30_days", label: "Last 30 days" },
  { value: "last_90_days", label: "Last 90 days" },
  { value: "this_month", label: "This month" },
  { value: "custom", label: "Custom" },
];

const DateRangeSelector = () => {
  const { preset, start, end, setPreset, setCustomRange } = useContext(DateRangeContext);

  const presetValue = useMemo(() => (preset === "custom" ? "custom" : preset), [preset]);

  return (
    <div className="dateRange">
      <label className="srOnly" htmlFor="date-range-preset">
        Date range
      </label>
      <select
        id="date-range-preset"
        className="controlSelect"
        value={presetValue}
        onChange={(e) => setPreset(e.target.value)}
      >
        {presets.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </select>

      {presetValue === "custom" ? (
        <div className="dateRangeCustom">
          <label className="srOnly" htmlFor="date-start">
            Start date
          </label>
          <input
            id="date-start"
            className="controlInput"
            type="date"
            value={start || ""}
            onChange={(e) => setCustomRange(e.target.value, end)}
          />
          <span className="dateRangeSep" aria-hidden="true">
            –
          </span>
          <label className="srOnly" htmlFor="date-end">
            End date
          </label>
          <input
            id="date-end"
            className="controlInput"
            type="date"
            value={end || ""}
            onChange={(e) => setCustomRange(start, e.target.value)}
          />
        </div>
      ) : null}
    </div>
  );
};

export default DateRangeSelector;

