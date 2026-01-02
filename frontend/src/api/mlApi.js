import { api } from "./generated/index.js";

const mlApi = {
  /**
   * @returns {Promise<import("./types").MlRevenueSeriesExportResponse>}
   */
  getRevenueSeriesExport: (params = {}) => api.ml.exportRevenueSeries(params),

  /**
   * @returns {Promise<import("./types").MlTransactionsExportResponse>}
   */
  getTransactionsExport: (params = {}) => api.ml.exportTransactions(params),

  getRevenueSeries: (params = {}) => api.ml.exportRevenueSeries(params),

  getTransactions: (params = {}) => api.ml.exportTransactions(params),

  /**
   * @returns {Promise<import("./types").MlLatestPredictionResponse>}
   */
  getLatestPrediction: (prediction_type, model_version) => api.ml.latestPrediction(prediction_type, model_version),
};

export default mlApi;
