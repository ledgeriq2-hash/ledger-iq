import axiosClient from "./axiosClient";

const feedbackApi = {
  async submit(payload) {
    const response = await axiosClient.post("/feedback/", payload);
    return response.data;
  },
  async listMine() {
    const response = await axiosClient.get("/feedback/");
    return response.data;
  },
};

export default feedbackApi;
