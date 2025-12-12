import axiosClient from "./axiosClient";

const invoicesApi = {
  async listInvoices(params = {}) {
    const response = await axiosClient.get("/invoices", { params });
    return response.data;
  },
  async getInvoice(id) {
    const response = await axiosClient.get(`/invoices/${id}`);
    return response.data;
  },
  async createInvoice(payload) {
    const response = await axiosClient.post("/invoices", payload);
    return response.data;
  },
  async updateInvoice(id, payload) {
    const response = await axiosClient.put(`/invoices/${id}`, payload);
    return response.data;
  },
  async deleteInvoice(id) {
    const response = await axiosClient.delete(`/invoices/${id}`);
    return response.data;
  },
};

export default invoicesApi;
