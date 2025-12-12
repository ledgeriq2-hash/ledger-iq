import axiosClient from "./axiosClient";

const portalApi = {
  async customerOverview(token) {
    const response = await axiosClient.get(`/portal/customer/${token}`);
    return response.data;
  },
  async customerInvoices(token) {
    const response = await axiosClient.get(`/portal/customer/${token}/invoices`);
    return response.data;
  },
  async customerPayments(token) {
    const response = await axiosClient.get(`/portal/customer/${token}/payments`);
    return response.data;
  },
  async customerSettings(token) {
    const response = await axiosClient.get(`/portal/customer/${token}/settings`);
    return response.data;
  },
  async supplierOverview(token) {
    const response = await axiosClient.get(`/portal/supplier/${token}`);
    return response.data;
  },
  async supplierOrders(token) {
    const response = await axiosClient.get(`/portal/supplier/${token}/orders`);
    return response.data;
  },
  async supplierPayments(token) {
    const response = await axiosClient.get(`/portal/supplier/${token}/payments`);
    return response.data;
  },
  async supplierSettings(token) {
    const response = await axiosClient.get(`/portal/supplier/${token}/settings`);
    return response.data;
  },
};

export default portalApi;
