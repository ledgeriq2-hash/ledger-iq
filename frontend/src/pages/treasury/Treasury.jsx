import React from "react";
import { useNavigate } from "react-router-dom";

import Card from "../../components/ui/Card.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";

const Treasury = () => {
  const navigate = useNavigate();

  return (
    <div className="u-grid u-gap-4">
      <div>
        <h1 className="u-m-0">Treasury</h1>
        <p className="u-text-muted u-m-0">Treasury is the single source of truth for cash, obligations, and timing.</p>
      </div>

      <Card title="Treasury workspace" subtitle="Connect accounts to begin reconciling positions.">
        <EmptyState
          compact
          title="No treasury data yet"
          message="Select a company to surface cash positions and upcoming obligations."
          actionLabel="Open treasury report"
          onAction={() => navigate("/reports")}
        />
      </Card>
    </div>
  );
};

export default Treasury;
