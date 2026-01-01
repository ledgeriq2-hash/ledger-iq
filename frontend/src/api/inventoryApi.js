import { api } from "./generated/index.js";

const inventoryApi = {
  listMovements: (params = {}) => api.inventory.listMovements(params),
  createMovement: (payload) => api.inventory.createMovement(payload),
  summary: () => api.inventory.summary(),
};

export default inventoryApi;
