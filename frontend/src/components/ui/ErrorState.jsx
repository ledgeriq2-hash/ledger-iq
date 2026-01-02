import React from "react";

import Button from "./Button.jsx";
import EmptyState from "./EmptyState.jsx";

const ErrorState = ({
  title = "Something went wrong",
  message,
  error,
  onRetry,
  retryLabel = "Retry",
  compact = false,
  action,
}) => {
  const resolvedMessage = message || error?.message || "Please try again.";

  const resolvedAction =
    action ||
    (onRetry ? (
      <Button size="sm" onClick={onRetry}>
        {retryLabel}
      </Button>
    ) : null);

  return <EmptyState title={title} message={resolvedMessage} action={resolvedAction} compact={compact} />;
};

export default ErrorState;
