import React from "react";
import colors from "../../design/colors.js";
import spacing from "../../design/spacing.js";
import typography from "../../design/typography.js";

const Input = ({ label, helper, error, dataTestId, ...props }) => {
  return (
    <label style={{ display: "grid", gap: spacing.xs, fontFamily: typography.fontFamily }}>
      {label && <span style={{ fontWeight: 600, color: colors.text }}>{label}</span>}
      <input
        style={{
          padding: spacing.sm,
          borderRadius: "8px",
          border: `1px solid ${error ? colors.danger : colors.border}`,
          fontFamily: typography.fontFamily,
        }}
        data-testid={dataTestId || props["data-testid"]}
        {...props}
      />
      {helper && <span style={{ color: colors.textMuted, fontSize: typography.small.size }}>{helper}</span>}
      {error && <span style={{ color: colors.danger, fontSize: typography.small.size }}>{error}</span>}
    </label>
  );
};

export default Input;
