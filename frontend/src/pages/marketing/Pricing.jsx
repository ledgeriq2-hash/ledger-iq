import React from "react";

const Plan = ({ name, price, features }) => (
  <div
    style={{
      background: "#fff",
      border: "1px solid #e2e8f0",
      borderRadius: "12px",
      padding: "1.5rem",
      display: "grid",
      gap: "0.6rem",
      minWidth: "240px",
    }}
  >
    <h3 style={{ margin: 0 }}>{name}</h3>
    <div style={{ fontSize: "2rem", fontWeight: 800, color: "#0f172a" }}>{price}</div>
    <ul style={{ margin: 0, paddingLeft: "1.1rem", color: "#475569", display: "grid", gap: "0.35rem" }}>
      {features.map((f) => (
        <li key={f}>{f}</li>
      ))}
    </ul>
    <a
      href="/signup"
      style={{
        marginTop: "0.5rem",
        background: "#0ea5e9",
        color: "#fff",
        padding: "0.75rem",
        textDecoration: "none",
        textAlign: "center",
        borderRadius: "10px",
        fontWeight: 700,
      }}
    >
      Choose plan
    </a>
  </div>
);

const Pricing = () => (
  <div style={{ fontFamily: "Inter, system-ui, sans-serif", background: "#f8fafc", minHeight: "100vh" }}>
    <header style={{ padding: "1.5rem", maxWidth: "1100px", margin: "0 auto", display: "flex", gap: "1rem" }}>
      <a href="/" style={{ color: "#0f172a", fontWeight: 800, textDecoration: "none" }}>
        Ledger IQ
      </a>
      <a href="/signup" style={{ marginLeft: "auto", color: "#0ea5e9", fontWeight: 700, textDecoration: "none" }}>
        Get started
      </a>
    </header>
    <main style={{ maxWidth: "1100px", margin: "0 auto", padding: "1.5rem", display: "grid", gap: "1.5rem" }}>
      <div>
        <h1 style={{ margin: 0, fontSize: "2.2rem", color: "#0f172a" }}>Simple pricing</h1>
        <p style={{ color: "#475569" }}>Pick the plan that fits your team today and scale later.</p>
      </div>
      <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))" }}>
        <Plan name="Free" price="$0" features={["Up to 3 users", "Customer portal", "AI previews"]} />
        <Plan
          name="Pro"
          price="$49"
          features={["25 users", "AI anomalies + forecasts", "Billing + portal payments", "Support SLA"]}
        />
      </div>
    </main>
  </div>
);

export default Pricing;
