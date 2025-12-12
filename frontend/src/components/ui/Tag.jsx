import React from "react";

const Tag = ({ children, tone = "default" }) => {
  const palette = {
    default: { bg: "#e2e8f0", color: "#0f172a" },
    success: { bg: "#dcfce7", color: "#166534" },
    warning: { bg: "#fef9c3", color: "#92400e" },
    danger: { bg: "#fee2e2", color: "#991b1b" },
  };
  const { bg, color } = palette[tone] || palette.default;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.25rem 0.5rem",
        borderRadius: "999px",
        background: bg,
        color,
        fontSize: "0.85rem",
        fontWeight: 600,
      }}
    >
      {children}
    </span>
  );
};

export default Tag;
