import axiosClient from "./axiosClient";

const onboardingApi = {
  async getStatus() {
    const response = await axiosClient.get("/onboarding/status");
    return response.data;
  },
  async updateStatus(payload) {
    const response = await axiosClient.post("/onboarding/status", payload);
    return response.data;
  },
  async createSampleData() {
    const response = await axiosClient.post("/onboarding/sample-data");
    return response.data;
  },
};

export default onboardingApi;
