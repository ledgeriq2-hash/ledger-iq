import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";

const NotFound = () => (
  <MainLayout>
    <div style={{ textAlign: "center", padding: "3rem" }}>
      <h2>404 — Not Found</h2>
      <p style={{ color: "#475569" }}>The page you requested could not be found.</p>
    </div>
  </MainLayout>
);

export default NotFound;
