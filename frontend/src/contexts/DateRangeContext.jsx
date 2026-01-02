import React, { createContext, useContext, useMemo, useState } from "react";

const DEFAULT_RANGE = { start: null, end: null, preset: "all" };

export const DateRangeContext = createContext({
  range: DEFAULT_RANGE,
  start: null,
  end: null,
  preset: "all",
  setRange: () => {},
  setPreset: () => {},
  setCustomRange: () => {},
  resetRange: () => {},
});

export const DateRangeProvider = ({ children }) => {
  const [range, setRangeState] = useState(DEFAULT_RANGE);

  const setRange = (next) => {
    if (typeof next === "function") {
      setRangeState((prev) => next(prev));
      return;
    }
    if (!next) {
      setRangeState(DEFAULT_RANGE);
      return;
    }
    setRangeState((prev) => ({ ...prev, ...next }));
  };

  const setPreset = (preset) => {
    setRangeState((prev) => ({ ...prev, preset }));
  };

  const setCustomRange = (start, end) => {
    setRangeState((prev) => ({
      ...prev,
      start: start || null,
      end: end || null,
      preset: "custom",
    }));
  };

  const resetRange = () => {
    setRangeState(DEFAULT_RANGE);
  };

  const value = useMemo(
    () => ({
      range,
      start: range.start,
      end: range.end,
      preset: range.preset,
      setRange,
      setPreset,
      setCustomRange,
      resetRange,
    }),
    [range]
  );

  return <DateRangeContext.Provider value={value}>{children}</DateRangeContext.Provider>;
};

export const useDateRange = () => useContext(DateRangeContext);
