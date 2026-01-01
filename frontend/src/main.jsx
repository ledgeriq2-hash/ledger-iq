import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import router from "./router.jsx";
import "./index.css";
import "./i18n/index.js";
import { NotificationProvider } from "./contexts/NotificationContext.jsx";
import NotificationHost from "./components/common/NotificationHost.jsx";
import { QueryClientProvider } from "@tanstack/react-query";
import queryClient from "./queryClient.js";
import { DateRangeProvider } from "./contexts/DateRangeContext.jsx";
import { AuthProvider } from "./contexts/AuthContext.jsx";

const applyInitialMode = () => {
  if (typeof document === "undefined") return;
  document.body.classList.add("theme-dark");
  document.body.classList.remove("theme-light");
  if (typeof window !== "undefined") {
    localStorage.setItem("app_mode", "dark");
  }
};

applyInitialMode();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <DateRangeProvider>
          <NotificationProvider>
            <NotificationHost />
            <RouterProvider router={router} />
          </NotificationProvider>
        </DateRangeProvider>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
