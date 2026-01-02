import React from "react";

const StatusPill = ({ tone = "info", children }) => {
  const toneClass =
    tone === "success"
      ? "kit-statusSuccess"
      : tone === "danger"
      ? "kit-statusDanger"
      : tone === "warning"
      ? "kit-statusWarning"
      : "kit-statusInfo";

  return <span className={`kit-statusPill ${toneClass}`.trim()}>{children}</span>;
};

export default StatusPill;

