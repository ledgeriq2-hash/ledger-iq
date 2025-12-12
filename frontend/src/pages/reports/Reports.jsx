import React from "react";
import MainLayout from "../../layouts/MainLayout.jsx";
import Card from "../../components/ui/Card.jsx";

const Reports = () => {
  return (
    <MainLayout>
      <h2>Reports</h2>
      <p style={{ color: "#475569" }}>Reporting dashboards are coming soon. Use admin overview for pilot monitoring.</p>
      <Card title="Empty state">
        <p style={{ color: "#475569", marginTop: 0 }}>
          Reports look better with activity. Create customers and invoices or use the onboarding wizard to load sample data.
        </p>
        <a href="/onboarding" style={{ color: "#2563eb", textDecoration: "none" }}>
          Launch onboarding →
        </a>
      </Card>
    </MainLayout>
  );
};

export default Reports;
