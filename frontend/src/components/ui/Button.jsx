import React from "react";
import colors from "../../design/colors.js";
import spacing from "../../design/spacing.js";
import typography from "../../design/typography.js";

const Button = ({ children, variant = "primary", disabled, style, dataTestId, ...props }) => {
  const palette =
    variant === "ghost"
      ? {
          background: "transparent",
          color: colors.primary,
          border: `1px solid ${colors.border}`,
        }
      : {
          background: colors.primary,
          color: "#fff",
          border: "none",
        };
  return (
    <button
      disabled={disabled}
      style={{
        padding: `${spacing.sm} ${spacing.lg}`,
        borderRadius: "10px",
        fontFamily: typography.fontFamily,
        fontWeight: 600,
        border: palette.border,
        background: palette.background,
        color: palette.color,
        opacity: disabled ? 0.65 : 1,
        cursor: disabled ? "not-allowed" : "pointer",
        transition: "transform 150ms ease, box-shadow 150ms ease",
        ...(dataTestId ? { "data-testid": dataTestId } : {}),
        ...style,
      }}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;
