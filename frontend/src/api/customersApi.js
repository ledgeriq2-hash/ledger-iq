import { api } from "./generated/index.js";

const customersApi = {
  listCustomers: (params = {}) => api.customers.listCustomers(params),
  getCustomer: (id) => api.customers.getCustomer(id),
  createCustomer: (payload) => api.customers.createCustomer(payload),
  updateCustomer: (id, payload) => api.customers.updateCustomer(id, payload),
  deleteCustomer: (id) => api.customers.deleteCustomer(id),
};

export default customersApi;
