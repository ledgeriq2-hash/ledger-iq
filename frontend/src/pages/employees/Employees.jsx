import React from "react";

import Card from "../../components/ui/Card.jsx";
import EmptyState from "../../components/ui/EmptyState.jsx";

const Employees = () => {
  return (
    <div className="u-grid u-gap-4">
      <div>
        <h1 className="u-m-0">Employees</h1>
        <p className="u-text-muted u-m-0">Keep people, roles, and approvals organized without accounting overhead.</p>
      </div>
      <Card title="Team directory" subtitle="Employee records will surface here once connected.">
        <EmptyState compact title="No employees yet" message="Invite a teammate to start building your approvals chain." />
      </Card>
    </div>
  );
};

export default Employees;
