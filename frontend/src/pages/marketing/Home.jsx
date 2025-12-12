import React from "react";

const Section = ({ title, children }) => (
  <section style={{ padding: "3rem 1.5rem", maxWidth: "1100px", margin: "0 auto" }}>
    <h2 style={{ fontSize: "2rem", marginBottom: "0.75rem", color: "#0f172a" }}>{title}</h2>
    <div style={{ color: "#475569", fontSize: "1.05rem", lineHeight: 1.6 }}>{children}</div>
  </section>
);

const Home = () => (
  <div style={{ fontFamily: "Inter, system-ui, sans-serif", background: "#f8fafc" }}>
    <header
      style={{
        padding: "1.5rem",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        maxWidth: "1100px",
        margin: "0 auto",
      }}
    >
      <div style={{ fontWeight: 800, fontSize: "1.4rem", color: "#0f172a" }}>Ledger IQ</div>
      <div style={{ display: "flex", gap: "0.75rem" }}>
        <a href="/pricing" style={{ color: "#0f172a", textDecoration: "none", fontWeight: 600 }}>
          Pricing
        </a>
        <a href="/signup" style={{ color: "#0ea5e9", fontWeight: 700, textDecoration: "none" }}>
          Get started
        </a>
      </div>
    </header>

    <section
      style={{
        padding: "3rem 1.5rem",
        background: "linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%)",
        color: "#e2e8f0",
      }}
    >
      <div style={{ maxWidth: "1100px", margin: "0 auto", display: "grid", gap: "1rem" }}>
        <h1 style={{ margin: 0, fontSize: "2.5rem" }}>Modern accounting, automated</h1>
        <p style={{ margin: 0, fontSize: "1.1rem", lineHeight: 1.6, maxWidth: "720px" }}>
          Ledger IQ brings billing, reporting, and AI insights together with secure portals for your customers and suppliers.
        </p>
        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <a
            href="/signup"
            style={{
              background: "#fff",
              color: "#0f172a",
              padding: "0.85rem 1.25rem",
              borderRadius: "10px",
              fontWeight: 700,
              textDecoration: "none",
            }}
          >
            Start free trial
          </a>
          <a
            href="/pricing"
            style={{
              color: "#e0f2fe",
              padding: "0.85rem 1rem",
              borderRadius: "10px",
              border: "1px solid rgba(255,255,255,0.3)",
              textDecoration: "none",
              fontWeight: 600,
            }}
          >
            View pricing
          </a>
        </div>
      </div>
    </section>

    <Section title="Everything you need to launch">
      <ul style={{ margin: 0, paddingLeft: "1.2rem", display: "grid", gap: "0.5rem" }}>
        <li>AI-powered anomaly detection and forecasting</li>
        <li>Customer and supplier portals with secure token access</li>
        <li>Role-based controls, audit logs, and MFA</li>
      </ul>
    </Section>
  </div>
);

export default Home;
