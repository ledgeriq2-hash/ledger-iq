import axiosClient from "./axiosClient";

const inventoryApi = {
  async listMovements(params = {}) {
    const res = await axiosClient.get("/inventory/movements", { params });
    return res.data;
  },
  async createMovement(payload) {
    const res = await axiosClient.post("/inventory/movements", payload);
    return res.data;
  },
  async summary() {
    const res = await axiosClient.get("/inventory/summary");
    return res.data;
  },
};

export default inventoryApi;
