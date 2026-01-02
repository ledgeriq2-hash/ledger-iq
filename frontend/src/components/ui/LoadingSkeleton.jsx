import React from "react";

import Skeleton from "./Skeleton.jsx";

const LoadingSkeleton = ({ variant = "card", rows = 3, label = "Loading..." }) => {
  if (variant === "table") {
    return (
      <div className="loadingSkeleton" role="status" aria-label={label}>
        {Array.from({ length: Math.max(3, rows) }).map((_, idx) => (
          <Skeleton key={idx} className="kit-skeletonLine loadingSkeletonLine" />
        ))}
      </div>
    );
  }

  if (variant === "chart") {
    return (
      <div className="loadingSkeleton" role="status" aria-label={label}>
        <Skeleton className="kit-skeletonChart" />
      </div>
    );
  }

  return (
    <div className="loadingSkeleton" role="status" aria-label={label}>
      <Skeleton className="kit-skeletonLg" />
      {Array.from({ length: Math.max(2, rows) }).map((_, idx) => (
        <Skeleton key={idx} className="kit-skeletonLine loadingSkeletonLine" />
      ))}
    </div>
  );
};

export default LoadingSkeleton;
