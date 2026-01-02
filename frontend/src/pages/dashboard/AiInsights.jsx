import React from "react";

import Card from "../../components/ui/Card.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";
import Skeleton from "../../components/ui/Skeleton.jsx";

const AiInsights = () => {
  return (
    <div className="portalGrid">
      <Card title="AI Insights" subtitle="Display-only placeholder">
        <div className="u-grid u-gap-3">
          <div className="dashboardMeta">Last updated: —</div>
          <EmptyState
            title="AI results will appear here once connected."
            message="This screen is read-only until the AI phase is enabled."
          />
          <div className="u-grid u-gap-2">
            <Skeleton className="kit-skeletonLg" />
            <Skeleton className="kit-skeletonLg" />
            <Skeleton className="kit-skeletonLg" />
          </div>
        </div>
      </Card>
    </div>
  );
};

export default AiInsights;

