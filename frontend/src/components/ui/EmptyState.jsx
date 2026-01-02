import React from "react";

import Button from "./Button.jsx";

const EmptyState = ({
  title = "No data",
  message = "Nothing to show yet.",
  action,
  actionLabel,
  onAction,
  compact = false,
}) => {
  const resolvedAction =
    action ||
    (actionLabel && onAction ? (
      <Button size="sm" onClick={onAction}>
        {actionLabel}
      </Button>
    ) : null);

  return (
    <div className="emptyState" data-compact={compact ? "true" : "false"}>
      <div className="emptyStateTitle">{title}</div>
      {message && <div className="emptyStateMessage">{message}</div>}
      {resolvedAction}
    </div>
  );
};

export default EmptyState;
