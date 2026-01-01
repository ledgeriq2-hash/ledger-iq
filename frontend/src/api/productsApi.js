import { api } from "./generated/index.js";

const productsApi = {
  listProducts: (params = {}) => api.products.listProducts(params),
  createProduct: (payload) => api.products.createProduct(payload),
};

export default productsApi;
