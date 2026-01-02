import { api } from "./generated/index.js";

const paymentsApi = {
  listPayments: (params = {}) => api.payments.listPayments(params),
  createPayment: (payload) => api.payments.createPayment(payload),
  getPayment: (id) => api.payments.getPayment(id),
  updatePayment: (id, payload) => api.payments.updatePayment(id, payload),
};

export default paymentsApi;
