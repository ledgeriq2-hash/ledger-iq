import { api } from "./generated/index.js";

const dashboardApi = {
  /**
   * @returns {Promise<import("./types").DashboardMetricsResponse>}
   */
  getMetrics: ({ months = 12, time_basis = "event_date" } = {}) => api.dashboard.getMetrics({ months, time_basis }),

  /**
   * @returns {Promise<import("./types").DashboardRecentTransactionsResponse>}
   */
  getRecentTransactions: ({ page = 1, page_size = 50 } = {}) =>
    api.dashboard.getRecentTransactions({ page, page_size }),
};

export default dashboardApi;
