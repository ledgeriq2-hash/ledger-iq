import axiosClient from "./axiosClient";

const customersApi = {
  async listCustomers(params = {}) {
    const response = await axiosClient.get("/customers", { params });
    return response.data;
  },
  async createCustomer(payload) {
    const response = await axiosClient.post("/customers", payload);
    return response.data;
  },
  async updateCustomer(id, payload) {
    const response = await axiosClient.put(`/customers/${id}`, payload);
    return response.data;
  },
  async deleteCustomer(id) {
    const response = await axiosClient.delete(`/customers/${id}`);
    return response.data;
  },
};

export default customersApi;
