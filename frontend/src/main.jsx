import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import router from "./router.jsx";
import "./index.css";
import { AuthProvider } from "./contexts/AuthContext.jsx";
import { NotificationProvider } from "./contexts/NotificationContext.jsx";
import NotificationHost from "./components/common/NotificationHost.jsx";
import { QueryClientProvider } from "@tanstack/react-query";
import queryClient from "./queryClient.js";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <NotificationProvider>
          <NotificationHost />
          <RouterProvider router={router} />
        </NotificationProvider>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
