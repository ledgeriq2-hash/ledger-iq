import React from "react";

const Skeleton = ({ className = "", label = "Loading..." }) => {
  return <div className={`kit-skeleton ${className}`.trim()} role="status" aria-label={label} />;
};

export default Skeleton;
