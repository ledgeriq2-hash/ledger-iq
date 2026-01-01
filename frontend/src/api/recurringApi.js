import { api } from "./generated/index.js";

const recurringApi = {
  list: (params = {}) => api.recurring.list(params),
  create: (payload) => api.recurring.create(payload),
  update: (id, payload) => api.recurring.update(id, payload),
  remove: (id) => api.recurring.remove(id),
  runNow: (id) => api.recurring.runNow(id),
};

export default recurringApi;
