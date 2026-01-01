import { api } from "./generated/index.js";

const billingApi = {
  /**
   * @returns {Promise<import("./types").BillingPlansResponse>}
   */
  listPlans: () => api.billing.listPlans(),
  /**
   * @returns {Promise<import("./types").BillingSubscriptionResponse>}
   */
  getSubscription: () => api.billing.getSubscription(),
  startCheckout: (planCode, successUrl, cancelUrl) => api.billing.startCheckout(planCode, successUrl, cancelUrl),
  /**
   * @returns {Promise<import("./types").BillingOverviewResponse>}
   */
  getOverview: () => api.billing.getOverview(),
};

export default billingApi;
