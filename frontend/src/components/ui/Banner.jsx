import React from "react";
import colors from "../../design/colors.js";
import spacing from "../../design/spacing.js";
import typography from "../../design/typography.js";

const variants = {
  info: { background: colors.surfaceMuted, border: colors.border, color: colors.text },
  warning: { background: "#fff7ed", border: "#fdba74", color: colors.warning },
  danger: { background: "#fef2f2", border: "#fecaca", color: colors.danger },
  success: { background: "#ecfdf3", border: "#bbf7d0", color: colors.success },
};

const Banner = ({ title, message, variant = "info", action }) => {
  const palette = variants[variant] || variants.info;
  return (
    <div
      style={{
        background: palette.background,
        border: `1px solid ${palette.border}`,
        borderRadius: "12px",
        padding: spacing.lg,
        color: palette.color,
        display: "grid",
        gap: spacing.xs,
        fontFamily: typography.fontFamily,
      }}
    >
      {title && <strong style={{ fontWeight: 700 }}>{title}</strong>}
      {message && <span>{message}</span>}
      {action}
    </div>
  );
};

export default Banner;
