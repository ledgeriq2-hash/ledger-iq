import React from "react";

const Footer = ({ appName = "Ledger IQ", buildText }) => {
  const year = new Date().getFullYear();
  return (
    <footer
      style={{
        padding: "1rem",
        textAlign: "center",
        borderTop: "1px solid #e5e7eb",
        color: "#475569",
        background: "#f8fafc",
        fontSize: "0.95rem",
      }}
    >
      {appName} © {year}
      {buildText ? ` · ${buildText}` : ""}
    </footer>
  );
};

export default Footer;

// Example:
// <Footer buildText="v1.2.3" />
