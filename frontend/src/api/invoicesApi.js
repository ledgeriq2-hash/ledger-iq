import { api } from "./generated/index.js";

const invoicesApi = {
  listInvoices: (params = {}) => api.invoices.listInvoices(params),
  getInvoice: (id) => api.invoices.getInvoice(id),
  createInvoice: (payload) => api.invoices.createInvoice(payload),
  updateInvoice: (id, payload) => api.invoices.updateInvoice(id, payload),
  deleteInvoice: (id) => api.invoices.deleteInvoice(id),
  postInvoice: (id) => api.invoices.postInvoice(id),
  recordPartialPayment: (id, payload) => api.invoices.recordPartialPayment(id, payload),
};

export default invoicesApi;
