import { api } from "./generated/index.js";

const authApi = {
  login: (data) => api.auth.login(data),
  register: (payload) => api.auth.register(payload),
  refresh: (payload = {}) => api.auth.refresh(payload),
  /**
   * @returns {Promise<import("./types").AuthMeResponse>}
   */
  me: () => api.auth.me(),
  async logout(payload = {}) {
    try {
      await api.auth.logout(payload);
    } catch (err) {
      // logout best-effort
      console.warn("Logout failed", err);
    }
  },
  logoutAll: () => api.auth.logoutAll(),
};

export default authApi;
