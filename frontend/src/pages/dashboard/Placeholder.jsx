import React from "react";

import Card from "../../components/kit/Card.jsx";
import StatusPill from "../../components/kit/StatusPill.jsx";

const Placeholder = ({ title }) => {
  return (
    <Card title={title}>
      <StatusPill tone="info">Coming soon</StatusPill>
    </Card>
  );
};

export default Placeholder;

