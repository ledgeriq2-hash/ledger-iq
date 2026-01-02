import { api } from "./generated/index.js";

const aiInsightsApi = {
  getSummary: () => api.ai.getSummary(),
  listInsights: (params = {}) => api.ai.listInsights(params),
  run: () => api.ai.run(),
};

export default aiInsightsApi;
