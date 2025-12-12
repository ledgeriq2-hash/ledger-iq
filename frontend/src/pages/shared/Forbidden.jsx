import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";

const Forbidden = () => (
  <MainLayout>
    <div style={{ textAlign: "center", padding: "3rem" }}>
      <h2>403 — Forbidden</h2>
      <p style={{ color: "#475569" }}>You do not have permission to access this page.</p>
    </div>
  </MainLayout>
);

export default Forbidden;
