import React from "react";
import { Navigate } from "react-router-dom";
import useAuth from "../../hooks/useAuth.js";
import usePermissions from "../../hooks/usePermissions.js";

/**
 * Wrap routes that require authentication and (optionally) certain roles.
 */
const ProtectedRoute = ({ children, requiredRoles }) => {
  const { isAuthenticated } = useAuth();
  const { hasRole } = usePermissions();
  const requiresRole = Array.isArray(requiredRoles) && requiredRoles.length > 0;
  const allowed = requiresRole ? requiredRoles.some((role) => hasRole(role)) : true;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!allowed) {
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
