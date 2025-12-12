import React from "react";
import { Navigate } from "react-router-dom";
import useAuth from "../../hooks/useAuth.js";

/**
 * Wrap routes that require authentication and (optionally) certain roles.
 */
const ProtectedRoute = ({ children, requiredRoles }) => {
  const { user, isAuthenticated } = useAuth();

  const hasRole =
    Array.isArray(requiredRoles) && requiredRoles.length > 0
      ? requiredRoles.some((role) => user?.roles?.includes?.(role))
      : true;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!hasRole) {
    return <Navigate to="/forbidden" replace />;
  }

  return children;
};

export default ProtectedRoute;

// Example (React Router v6):
// {
//   path: "/dashboard",
//   element: (
//     <ProtectedRoute>
//       <Dashboard />
//     </ProtectedRoute>
//   ),
// }
//
// {
//   path: "/admin",
//   element: (
//     <ProtectedRoute requiredRoles={["admin"]}>
//       <AdminPage />
//     </ProtectedRoute>
//   ),
// }
