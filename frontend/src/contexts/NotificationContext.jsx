import React, { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { setErrorNotifier } from "../api/axiosClient.js";

export const NotificationContext = createContext({
  notifications: [],
  addNotification: () => {},
  removeNotification: () => {},
  clearNotifications: () => {},
});

export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);

  const addNotification = useCallback((notification) => {
    setNotifications((prev) => [...prev, { id: crypto.randomUUID(), ...notification }]);
  }, []);

  const removeNotification = useCallback((id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  }, []);

  const clearNotifications = useCallback(() => setNotifications([]), []);

  const value = useMemo(
    () => ({ notifications, addNotification, removeNotification, clearNotifications }),
    [notifications, addNotification, removeNotification, clearNotifications]
  );

  useEffect(() => {
    setErrorNotifier((note) => {
      addNotification({
        title: note?.title || "Request failed",
        message: note?.message || "Unexpected error occurred.",
      });
    });
    return () => setErrorNotifier(null);
  }, [addNotification]);

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
};
