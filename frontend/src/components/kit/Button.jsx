import React from "react";

const Button = ({ variant = "primary", className = "", ...props }) => {
  const variantClass =
    variant === "secondary"
      ? "kit-buttonSecondary"
      : variant === "ghost"
      ? "kit-buttonGhost"
      : "kit-buttonPrimary";

  return <button className={`kit-button ${variantClass} ${className}`.trim()} {...props} />;
};

export default Button;

