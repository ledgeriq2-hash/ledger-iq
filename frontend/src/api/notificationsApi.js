import { api } from "./generated/index.js";

const notificationsApi = {
  list: () => api.notifications.list(),
  markRead: (notificationId) => api.notifications.markRead(notificationId),
};

export default notificationsApi;
