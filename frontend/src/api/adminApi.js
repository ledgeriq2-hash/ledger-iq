import axiosClient from "./axiosClient";

const adminApi = {
  async listTenants() {
    const response = await axiosClient.get("/admin/tenants/");
    return response.data;
  },
  async enableSoftLaunch(tenantId) {
    const response = await axiosClient.post(`/admin/tenants/${tenantId}/soft-launch/enable`);
    return response.data;
  },
  async disableSoftLaunch(tenantId) {
    const response = await axiosClient.post(`/admin/tenants/${tenantId}/soft-launch/disable`);
    return response.data;
  },
  async tenantOverview(tenantId) {
    const response = await axiosClient.get(`/admin/tenants/${tenantId}/overview`);
    return response.data;
  },
  async recentErrors(limit = 100) {
    const response = await axiosClient.get("/admin/errors/recent", { params: { limit } });
    return response.data;
  },
  async adminFeedback(params = {}) {
    const response = await axiosClient.get("/admin/feedback", { params });
    return response.data;
  },
  async tenantFeedback(tenantId, limit = 50) {
    const response = await axiosClient.get(`/admin/tenants/${tenantId}/feedback`, { params: { limit } });
    return response.data;
  },
};

export default adminApi;
