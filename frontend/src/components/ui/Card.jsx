import React from "react";
import colors from "../../design/colors.js";
import spacing from "../../design/spacing.js";
import typography from "../../design/typography.js";

const Card = ({ title, children, style }) => {
  return (
    <div
      style={{
        background: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: "12px",
        padding: spacing.lg,
        boxShadow: "0 10px 30px rgba(15,23,42,0.05)",
        ...style,
      }}
    >
      {title && (
        <h3
          style={{
            marginTop: 0,
            marginBottom: spacing.sm,
            fontFamily: typography.fontFamily,
            fontWeight: typography.heading.weight,
            fontSize: typography.heading.size,
            color: colors.text,
          }}
        >
          {title}
        </h3>
      )}
      {children}
    </div>
  );
};

export default Card;
