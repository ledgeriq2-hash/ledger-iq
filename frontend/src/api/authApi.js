import axiosClient from "./axiosClient";

const authApi = {
  async login(data) {
    const response = await axiosClient.post("/auth/login", data);
    return response.data;
  },
  async refresh(payload = {}) {
    const response = await axiosClient.post("/auth/refresh", payload);
    return response.data;
  },
  async me() {
    const response = await axiosClient.get("/auth/me");
    return response.data;
  },
  async logout(payload = {}) {
    try {
      await axiosClient.post("/auth/logout", payload);
    } catch (err) {
      // logout best-effort
      console.warn("Logout failed", err);
    }
  },
};

export default authApi;
