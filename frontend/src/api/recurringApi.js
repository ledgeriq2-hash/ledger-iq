import axiosClient from "./axiosClient";

const base = "/recurring-invoices";

const recurringApi = {
  async list(params = {}) {
    const response = await axiosClient.get(base + "/", { params });
    return response.data;
  },
  async create(payload) {
    const response = await axiosClient.post(base + "/", payload);
    return response.data;
  },
  async update(id, payload) {
    const response = await axiosClient.patch(`${base}/${id}`, payload);
    return response.data;
  },
  async remove(id) {
    const response = await axiosClient.delete(`${base}/${id}`);
    return response.data;
  },
  async runNow(id) {
    const response = await axiosClient.post(`${base}/${id}/run`);
    return response.data;
  },
};

export default recurringApi;
