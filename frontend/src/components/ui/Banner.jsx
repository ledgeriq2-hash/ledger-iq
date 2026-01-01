import React from "react";

const Banner = ({ title, message, variant = "info", action }) => {
  const safeVariant =
    variant === "warning" || variant === "danger" || variant === "success" ? variant : "info";
  return (
    <div className="banner" data-variant={safeVariant}>
      {title && <strong className="bannerTitle">{title}</strong>}
      {message && <span>{message}</span>}
      {action}
    </div>
  );
};

export default Banner;
