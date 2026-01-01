import { api } from "./generated/index.js";

const onboardingApi = {
  getStatus: () => api.onboarding.getStatus(),
  updateStatus: (payload) => api.onboarding.updateStatus(payload),
  createSampleData: () => api.onboarding.createSampleData(),
};

export default onboardingApi;
