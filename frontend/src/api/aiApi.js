import { api } from "./generated/index.js";

const aiApi = {
  overview: () => api.ai.overview(),
  summary: (params) => api.ai.summary(params),
  forecast: (payload) => api.ai.forecast(payload),
  anomalies: (payload) => api.ai.anomalies(payload),
  listLogs: (params = {}) => api.ai.listLogs(params),
  listRuns: (params = {}) => api.ai.listRuns(params),
  getLog: (id) => api.ai.getLog(id),
};

export default aiApi;
