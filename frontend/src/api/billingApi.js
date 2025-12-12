import axiosClient from "./axiosClient";

const billingApi = {
  async listPlans() {
    const response = await axiosClient.get("/billing/plans");
    return response.data;
  },
  async getSubscription() {
    const response = await axiosClient.get("/billing/subscription");
    return response.data;
  },
  async startCheckout(planCode, successUrl, cancelUrl) {
    const response = await axiosClient.post("/billing/checkout", {
      plan_code: planCode,
      success_url: successUrl,
      cancel_url: cancelUrl,
    });
    return response.data;
  },
};

export default billingApi;
