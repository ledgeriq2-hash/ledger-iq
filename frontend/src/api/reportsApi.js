import { api } from "./generated/index.js";

const reportsApi = {
  clientStatement: (params) => api.reports.clientStatement(params),
  treasuryReport: (params = {}) => api.reports.treasuryReport(params),
};

export default reportsApi;
