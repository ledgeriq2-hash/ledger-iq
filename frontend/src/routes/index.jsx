import React from "react";
import { Navigate } from "react-router-dom";
import App from "../App.jsx";
import Login from "../pages/auth/Login.jsx";
import useAuth from "../hooks/useAuth.js";
import DashboardBasic from "../pages/basic/DashboardBasic.jsx";
import CustomersBasic from "../pages/basic/CustomersBasic.jsx";
import InvoicesBasic from "../pages/basic/InvoicesBasic.jsx";
import PaymentsBasic from "../pages/basic/PaymentsBasic.jsx";
import Reports from "../pages/reports/Reports.jsx";
import TenantsList from "../pages/admin/TenantsList.jsx";
import TenantOverview from "../pages/admin/TenantOverview.jsx";
import FeedbackList from "../pages/admin/FeedbackList.jsx";
import ErrorBoundary from "../components/common/ErrorBoundary.jsx";
import Forbidden from "../pages/shared/Forbidden.jsx";
import NotFound from "../pages/shared/NotFound.jsx";
import Billing from "../pages/settings/Billing.jsx";
import OnboardingWizard from "../pages/onboarding/OnboardingWizard.jsx";
import CustomerPortal from "../pages/portal/CustomerPortal.jsx";
import SupplierPortal from "../pages/portal/SupplierPortal.jsx";
import CustomerOverview from "../pages/portal/customer/Overview.jsx";
import CustomerInvoices from "../pages/portal/customer/Invoices.jsx";
import CustomerPayments from "../pages/portal/customer/Payments.jsx";
import CustomerSettings from "../pages/portal/customer/Settings.jsx";
import SupplierOverview from "../pages/portal/supplier/Overview.jsx";
import SupplierOrders from "../pages/portal/supplier/Orders.jsx";
import SupplierPayments from "../pages/portal/supplier/Payments.jsx";
import SupplierSettings from "../pages/portal/supplier/Settings.jsx";
import Home from "../pages/marketing/Home.jsx";
import Pricing from "../pages/marketing/Pricing.jsx";
import Signup from "../pages/auth/Signup.jsx";
import AIOverview from "../pages/shared/AIOverview.jsx";
import RecurringInvoices from "../pages/advanced/RecurringInvoices.jsx";
import Inventory from "../pages/advanced/Inventory.jsx";

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <div>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
};

const routes = [
  {
    path: "/portal/customer/:token",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <CustomerPortal />
      </React.Suspense>
    ),
    children: [
      { index: true, element: <CustomerOverview /> },
      { path: "invoices", element: <CustomerInvoices /> },
      { path: "payments", element: <CustomerPayments /> },
      { path: "settings", element: <CustomerSettings /> },
    ],
  },
  {
    path: "/portal/supplier/:token",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <SupplierPortal />
      </React.Suspense>
    ),
    children: [
      { index: true, element: <SupplierOverview /> },
      { path: "orders", element: <SupplierOrders /> },
      { path: "payments", element: <SupplierPayments /> },
      { path: "settings", element: <SupplierSettings /> },
    ],
  },
  {
    path: "/pricing",
    element: <Pricing />,
  },
  {
    path: "/signup",
    element: <Signup />,
  },
  {
    path: "/",
    element: <Home />,
  },
  {
    path: "/login",
    element: (
      <React.Suspense fallback={<div>Loading...</div>}>
        <Login />
      </React.Suspense>
    ),
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <ErrorBoundary>
          <React.Suspense fallback={<div>Loading...</div>}>
            <App />
          </React.Suspense>
        </ErrorBoundary>
      </ProtectedRoute>
    ),
    errorElement: <NotFound />,
    children: [
      {
        index: true,
        element: <DashboardBasic />,
      },
      {
        path: "customers",
        element: <CustomersBasic />,
      },
      {
        path: "invoices",
        element: <InvoicesBasic />,
      },
      {
        path: "recurring-invoices",
        element: <RecurringInvoices />,
      },
      {
        path: "inventory",
        element: <Inventory />,
      },
      {
        path: "payments",
        element: <PaymentsBasic />,
      },
      {
        path: "billing",
        element: <Billing />,
      },
      {
        path: "onboarding",
        element: <OnboardingWizard />,
      },
      {
        path: "reports",
        element: <Reports />,
      },
      {
        path: "ai/overview",
        element: <AIOverview />,
      },
      {
        path: "admin/tenants",
        element: <TenantsList />,
      },
      {
        path: "admin/tenants/:id",
        element: <TenantOverview />,
      },
      {
        path: "admin/feedback",
        element: <FeedbackList />,
      },
      {
        path: "403",
        element: <Forbidden />,
      },
      {
        path: "*",
        element: <NotFound />,
      },
    ],
  },
];

export default routes;
