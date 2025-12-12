import axiosClient from "./axiosClient";

const productsApi = {
  async listProducts(params = {}) {
    const res = await axiosClient.get("/products/", { params });
    return res.data;
  },
  async createProduct(payload) {
    const res = await axiosClient.post("/products/", payload);
    return res.data;
  },
};

export default productsApi;
