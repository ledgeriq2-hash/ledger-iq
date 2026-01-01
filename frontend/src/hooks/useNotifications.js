import { useContext } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import notificationsApi from "../api/notificationsApi.js";
import { NotificationContext } from "../contexts/NotificationContext.jsx";

export const useNotificationsQuery = ({ enabled = true } = {}) =>
  useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationsApi.list(),
    enabled,
    staleTime: 15_000,
  });

export const useMarkNotificationRead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId) => notificationsApi.markRead(notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
};

const useNotifications = () => useContext(NotificationContext);

export default useNotifications;
