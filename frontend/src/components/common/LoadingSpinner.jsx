import React from "react";

const LoadingSpinner = ({ message = "Loading..." }) => (
  <div className="spinnerWrap" role="status" aria-live="polite">
    <div className="spinner" aria-hidden="true" />
    {message && <div className="spinnerText">{message}</div>}
  </div>
);

export default LoadingSpinner;

// Example:
// <LoadingSpinner message="Fetching data..." />
