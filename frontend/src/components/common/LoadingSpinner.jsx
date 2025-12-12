import React from "react";

const spinnerStyle = {
  width: "48px",
  height: "48px",
  border: "4px solid #e5e7eb",
  borderTop: "4px solid #6366f1",
  borderRadius: "50%",
  animation: "spin 1s linear infinite",
};

const containerStyle = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  padding: "2rem",
  gap: "0.75rem",
};

const textStyle = {
  color: "#4b5563",
  fontSize: "0.95rem",
};

const LoadingSpinner = ({ message = "Loading..." }) => (
  <div style={containerStyle} role="status" aria-live="polite">
    <div style={spinnerStyle} />
    {message && <div style={textStyle}>{message}</div>}
    <style>
      {`@keyframes spin { to { transform: rotate(360deg); } }`}
    </style>
  </div>
);

export default LoadingSpinner;

// Example:
// <LoadingSpinner message="Fetching data..." />
