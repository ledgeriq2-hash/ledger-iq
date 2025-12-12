import React from "react";

const AuthLayout = ({ children }) => {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "stretch",
        justifyContent: "center",
        background: "radial-gradient(circle at 20% 20%, rgba(56,189,248,0.08), transparent 35%), radial-gradient(circle at 80% 0%, rgba(14,165,233,0.06), transparent 25%), #0f172a",
        color: "#e2e8f0",
        padding: "2rem",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.1fr 0.9fr",
          gap: "1.25rem",
          width: "100%",
          maxWidth: "960px",
        }}
      >
        <div
          style={{
            background: "linear-gradient(135deg, rgba(14,165,233,0.16), rgba(56,189,248,0.06))",
            borderRadius: "16px",
            padding: "2rem",
            border: "1px solid rgba(226,232,240,0.1)",
            display: "grid",
            gap: "0.75rem",
          }}
        >
          <div style={{ fontSize: "0.85rem", color: "#bae6fd", letterSpacing: "0.04em" }}>LEDGER IQ</div>
          <h2 style={{ margin: 0, fontSize: "1.8rem" }}>Modern finance workspace</h2>
          <p style={{ margin: 0, color: "#cbd5e1" }}>
            Track invoices, collaborate with your team, and let our AI co-pilot spot anomalies before they turn into issues.
          </p>
          <ul style={{ margin: 0, paddingLeft: "1.2rem", color: "#e2e8f0", display: "grid", gap: "0.35rem" }}>
            <li>Role-based access with audit-ready history</li>
            <li>Billing, reports, and portal in one place</li>
            <li>Guided onboarding to get you live in minutes</li>
          </ul>
        </div>
        <div
          style={{
            background: "#111827",
            padding: "2rem",
            borderRadius: "16px",
            boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
            width: "100%",
            border: "1px solid rgba(255,255,255,0.04)",
          }}
        >
          <div style={{ marginBottom: "1.5rem", textAlign: "center" }}>
            <h1 style={{ margin: 0, fontSize: "1.6rem" }}>Welcome back</h1>
            <p style={{ margin: "0.35rem 0 0", color: "#94a3b8", fontSize: "0.95rem" }}>
              Sign in or continue onboarding
            </p>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;
