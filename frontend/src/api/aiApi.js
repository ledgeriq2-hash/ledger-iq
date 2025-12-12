import axiosClient from "./axiosClient";

const aiApi = {
  forecast: (data) => axiosClient.post("/ai/forecast", data),
  anomalies: (data) => axiosClient.post("/ai/anomaly", data),
  logs: () => axiosClient.get("/ai/logs"),
  summary: (payload) => axiosClient.post("/ai/summary", payload),
};

export default aiApi;
