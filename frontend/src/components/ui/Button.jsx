import React from "react";

const Button = ({
  children,
  variant = "primary",
  size = "md",
  disabled,
  className = "",
  dataTestId,
  ...props
}) => {
  const variantClass =
    variant === "secondary"
      ? "kit-buttonSecondary"
      : variant === "ghost"
        ? "kit-buttonGhost"
        : "kit-buttonPrimary";

  const sizeClass = size === "sm" ? "kit-buttonSm" : size === "lg" ? "kit-buttonLg" : "kit-buttonMd";

  return (
    <button
      type={props.type || "button"}
      disabled={disabled}
      data-testid={dataTestId || props["data-testid"]}
      className={`kit-button ${variantClass} ${sizeClass} ${className}`.trim()}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;
