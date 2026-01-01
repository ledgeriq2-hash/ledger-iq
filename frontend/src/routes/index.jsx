import React from "react";
import { Navigate } from "react-router-dom";

import NotFound from "../pages/shared/NotFound.jsx";
import Portal from "../pages/portal/Portal.jsx";
import MainLayout from "../layouts/MainLayout.jsx";
import Dashboard from "../pages/dashboard/Dashboard.jsx";
import Clients from "../pages/dashboard/Clients.jsx";
import ClientDetails from "../pages/dashboard/ClientDetails.jsx";
import Suppliers from "../pages/dashboard/Suppliers.jsx";
import Invoices from "../pages/dashboard/Invoices.jsx";
import Settings from "../pages/dashboard/Settings.jsx";
import AIOverview from "../pages/shared/AIOverview.jsx";
import Reports from "../pages/reports/Reports.jsx";
import Payments from "../pages/payments/Payments.jsx";
import Inventory from "../pages/advanced/Inventory.jsx";
import Treasury from "../pages/treasury/Treasury.jsx";
import Employees from "../pages/employees/Employees.jsx";
import Notifications from "../pages/shared/Notifications.jsx";
import TenantsList from "../pages/admin/TenantsList.jsx";
import TenantOverview from "../pages/admin/TenantOverview.jsx";
import FeedbackList from "../pages/admin/FeedbackList.jsx";
import ModelRuns from "../pages/modelRuns/ModelRuns.jsx";
import Predictions from "../pages/predictions/Predictions.jsx";
import DataAssessment from "../pages/dataAssessment/DataAssessment.jsx";
import Exports from "../pages/exports/Exports.jsx";
import TenantSelect from "../pages/onboarding/TenantSelect.jsx";

const routes = [
  {
    path: "/onboarding/tenant",
    element: <TenantSelect />,
  },
  {
    path: "/portal/:token/*",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <Portal />
      </React.Suspense>
    ),
  },
  {
    path: "/portal",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <Portal />
      </React.Suspense>
    ),
  },
  {
    path: "/",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <MainLayout />
      </React.Suspense>
    ),
    errorElement: <NotFound />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      { path: "dashboard", element: <Dashboard /> },
      { path: "treasury", element: <Treasury /> },
      { path: "ai", element: <AIOverview /> },
      { path: "customers", element: <Clients /> },
      { path: "customers/:id", element: <ClientDetails /> },
      { path: "invoices", element: <Invoices /> },
      { path: "payments", element: <Payments /> },
      { path: "inventory", element: <Inventory /> },
      { path: "suppliers", element: <Suppliers /> },
      { path: "employees", element: <Employees /> },
      { path: "reports", element: <Reports /> },
      { path: "settings", element: <Settings /> },
      { path: "notifications", element: <Notifications /> },
      { path: "admin", element: <TenantsList /> },
      { path: "admin/tenants/:id", element: <TenantOverview /> },
      { path: "admin/feedback", element: <FeedbackList /> },
      { path: "predictions", element: <Predictions /> },
      { path: "model-runs", element: <ModelRuns /> },
      { path: "data", element: <DataAssessment /> },
      { path: "exports", element: <Exports /> },
      { path: "*", element: <NotFound /> },
    ],
  },
];

export default routes;
