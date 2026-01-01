import React from "react";

const Tag = ({ children, tone = "default" }) => {
  const safeTone = tone === "success" || tone === "warning" || tone === "danger" ? tone : "default";
  return (
    <span className="tag" data-tone={safeTone}>
      {children}
    </span>
  );
};

export default Tag;
