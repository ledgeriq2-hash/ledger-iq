import { api } from "./generated/index.js";

const adminApi = {
  listTenants: (params = {}) => api.admin.listTenants(params),
  enableSoftLaunch: (tenantId) => api.admin.enableSoftLaunch(tenantId),
  disableSoftLaunch: (tenantId) => api.admin.disableSoftLaunch(tenantId),
  tenantOverview: (tenantId) => api.admin.tenantOverview(tenantId),
  recentErrors: (limit = 100) => api.admin.recentErrors(limit),
  adminFeedback: (params = {}) => api.admin.adminFeedback(params),
  tenantFeedback: (tenantId, limit = 50) => api.admin.tenantFeedback(tenantId, limit),
};

export default adminApi;
