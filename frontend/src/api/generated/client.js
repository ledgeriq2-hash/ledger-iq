import axiosClient from "../index";

const applyPathParams = (path, pathParams) => {
  if (!pathParams || typeof path !== "string") return path;
  return Object.entries(pathParams).reduce((acc, [key, value]) => {
    const encoded = encodeURIComponent(String(value));
    return acc.replace("{" + key + "}", encoded);
  }, path);
};

const buildPortalHeaders = (token) => {
  if (!token) return undefined;
  return { "X-Portal-Token": token };
};

const request = async ({ method, path, pathParams, query, body, headers: extraHeaders }) => {
  const resolvedPath = applyPathParams(path, pathParams);
  const config = {
    url: resolvedPath,
    method,
    params: query,
    headers: { ...(extraHeaders || {}) },
    skipTenant: resolvedPath.startsWith("/api/v1/portal/"),
  };
  if (body !== undefined) {
    config.data = body;
  }

  const response = await axiosClient.request(config);
  return response?.data ?? null;
};

export const api = {
  auth: {
    login: async (payload) => request({ method: "POST", path: "/api/v1/auth/login", body: payload }),
    register: async (payload) => request({ method: "POST", path: "/api/v1/auth/register", body: payload }),
    refresh: async (payload = {}) => request({ method: "POST", path: "/api/v1/auth/refresh", body: payload }),
    me: async () => request({ method: "GET", path: "/api/v1/auth/me" }),
    logout: async (payload = {}) => request({ method: "POST", path: "/api/v1/auth/logout", body: payload }),
    logoutAll: async () => request({ method: "POST", path: "/api/v1/auth/logout-all" }),
  },
  settings: {
    getSettings: async () => request({ method: "GET", path: "/api/settings" }),
    updateSettings: async (payload) => request({ method: "PUT", path: "/api/settings", body: payload }),
  },
  admin: {
    listTenants: async (params = {}) => request({ method: "GET", path: "/api/v1/admin/tenants/", query: params }),
    enableSoftLaunch: async (tenantId) =>
      request({
        method: "POST",
        path: "/api/v1/admin/tenants/{tenant_id}/soft-launch/enable",
        pathParams: { tenant_id: tenantId },
      }),
    disableSoftLaunch: async (tenantId) =>
      request({
        method: "POST",
        path: "/api/v1/admin/tenants/{tenant_id}/soft-launch/disable",
        pathParams: { tenant_id: tenantId },
      }),
    tenantOverview: async (tenantId) =>
      request({
        method: "GET",
        path: "/api/v1/admin/tenants/{tenant_id}/overview",
        pathParams: { tenant_id: tenantId },
      }),
    recentErrors: async (limit = 100) =>
      request({ method: "GET", path: "/api/v1/admin/errors/recent", query: { limit } }),
    adminFeedback: async (params = {}) => request({ method: "GET", path: "/api/v1/admin/feedback", query: params }),
    tenantFeedback: async (tenantId, limit = 50) =>
      request({
        method: "GET",
        path: "/api/v1/admin/tenants/{tenant_id}/feedback",
        pathParams: { tenant_id: tenantId },
        query: { limit },
      }),
  },
  billing: {
    listPlans: async () => request({ method: "GET", path: "/api/v1/billing/plans" }),
    getSubscription: async () => request({ method: "GET", path: "/api/v1/billing/subscription" }),
    startCheckout: async (planCode, successUrl, cancelUrl) =>
      request({
        method: "POST",
        path: "/api/v1/billing/checkout",
        body: { plan_code: planCode, success_url: successUrl, cancel_url: cancelUrl },
      }),
    getOverview: async () => request({ method: "GET", path: "/api/v1/billing/overview" }),
  },
  customers: {
    listCustomers: async ({ page = 1, page_size = 50 } = {}) =>
      request({ method: "GET", path: "/api/v1/customers/", query: { page, page_size } }),
    getCustomer: async (id) =>
      request({ method: "GET", path: "/api/v1/customers/{customer_id}", pathParams: { customer_id: id } }),
    createCustomer: async (payload) => request({ method: "POST", path: "/api/v1/customers/", body: payload }),
    updateCustomer: async (id, payload) =>
      request({
        method: "PUT",
        path: "/api/v1/customers/{customer_id}",
        pathParams: { customer_id: id },
        body: payload,
      }),
    deleteCustomer: async (id) =>
      request({ method: "DELETE", path: "/api/v1/customers/{customer_id}", pathParams: { customer_id: id } }),
  },
  employees: {
    listEmployees: async ({ page = 1, page_size = 50 } = {}) =>
      request({ method: "GET", path: "/api/v1/employees/", query: { page, page_size } }),
    getEmployee: async (id) =>
      request({ method: "GET", path: "/api/v1/employees/{employee_id}", pathParams: { employee_id: id } }),
    createEmployee: async (payload) => request({ method: "POST", path: "/api/v1/employees/", body: payload }),
    updateEmployee: async (id, payload) =>
      request({
        method: "PUT",
        path: "/api/v1/employees/{employee_id}",
        pathParams: { employee_id: id },
        body: payload,
      }),
    deleteEmployee: async (id) =>
      request({
        method: "DELETE",
        path: "/api/v1/employees/{employee_id}",
        pathParams: { employee_id: id },
      }),
  },
  suppliers: {
    listSuppliers: async ({ page = 1, page_size = 50 } = {}) =>
      request({ method: "GET", path: "/api/v1/suppliers/", query: { page, page_size } }),
    createSupplier: async (payload) => request({ method: "POST", path: "/api/v1/suppliers/", body: payload }),
    getSupplier: async (id) =>
      request({ method: "GET", path: "/api/v1/suppliers/{supplier_id}", pathParams: { supplier_id: id } }),
    updateSupplier: async (id, payload) =>
      request({
        method: "PUT",
        path: "/api/v1/suppliers/{supplier_id}",
        pathParams: { supplier_id: id },
        body: payload,
      }),
    deleteSupplier: async (id) =>
      request({ method: "DELETE", path: "/api/v1/suppliers/{supplier_id}", pathParams: { supplier_id: id } }),
  },
  debts: {
    listDebts: async ({ page = 1, page_size = 50, status } = {}) =>
      request({ method: "GET", path: "/api/v1/debts/", query: { page, page_size, status } }),
    getDebt: async (id) =>
      request({ method: "GET", path: "/api/v1/debts/{debt_id}", pathParams: { debt_id: id } }),
    createDebt: async (payload) => request({ method: "POST", path: "/api/v1/debts/", body: payload }),
    updateDebt: async (id, payload) =>
      request({
        method: "PUT",
        path: "/api/v1/debts/{debt_id}",
        pathParams: { debt_id: id },
        body: payload,
      }),
    deleteDebt: async (id) =>
      request({ method: "DELETE", path: "/api/v1/debts/{debt_id}", pathParams: { debt_id: id } }),
    recordPayment: async (id, payload) =>
      request({
        method: "POST",
        path: "/api/v1/debts/{debt_id}/payments",
        pathParams: { debt_id: id },
        body: payload,
      }),
  },
  reports: {
    clientStatement: async ({ client_id, from_date, to_date } = {}) =>
      request({ method: "GET", path: "/api/v1/reports/client-statement", query: { client_id, from_date, to_date } }),
    treasuryReport: async (query = {}) => request({ method: "GET", path: "/api/v1/reports/treasury", query }),
  },
  invoices: {
    listInvoices: async ({ page = 1, page_size = 50 } = {}) =>
      request({ method: "GET", path: "/api/v1/invoices/", query: { page, page_size } }),
    getInvoice: async (id) =>
      request({ method: "GET", path: "/api/v1/invoices/{invoice_id}", pathParams: { invoice_id: id } }),
    createInvoice: async (payload) => request({ method: "POST", path: "/api/v1/invoices/", body: payload }),
    postInvoice: async (id) =>
      request({ method: "POST", path: "/api/v1/invoices/{invoice_id}/post", pathParams: { invoice_id: id } }),
    updateInvoice: async (id, payload) =>
      request({
        method: "PUT",
        path: "/api/v1/invoices/{invoice_id}",
        pathParams: { invoice_id: id },
        body: payload,
      }),
    deleteInvoice: async (id) =>
      request({ method: "DELETE", path: "/api/v1/invoices/{invoice_id}", pathParams: { invoice_id: id } }),
    recordPartialPayment: async (id, payload) =>
      request({
        method: "POST",
        path: "/api/v1/invoices/{invoice_id}/payments",
        pathParams: { invoice_id: id },
        body: payload,
      }),
  },
  payments: {
    listPayments: async (params = {}) => request({ method: "GET", path: "/api/v1/payments/", query: params }),
    createPayment: async (payload) => request({ method: "POST", path: "/api/v1/payments/", body: payload }),
    getPayment: async (id) =>
      request({ method: "GET", path: "/api/v1/payments/{payment_id}", pathParams: { payment_id: id } }),
    updatePayment: async (id, payload) =>
      request({
        method: "PUT",
        path: "/api/v1/payments/{payment_id}",
        pathParams: { payment_id: id },
        body: payload,
      }),
  },
  products: {
    listProducts: async (params = {}) => request({ method: "GET", path: "/api/v1/products/", query: params }),
    createProduct: async (payload) => request({ method: "POST", path: "/api/v1/products/", body: payload }),
  },
  inventory: {
    listMovements: async (params = {}) =>
      request({ method: "GET", path: "/api/v1/inventory/movements", query: params }),
    createMovement: async (payload) => request({ method: "POST", path: "/api/v1/inventory/movements", body: payload }),
    summary: async () => request({ method: "GET", path: "/api/v1/inventory/summary" }),
  },
  recurring: {
    list: async (params = {}) => request({ method: "GET", path: "/api/v1/recurring-invoices/", query: params }),
    create: async (payload) => request({ method: "POST", path: "/api/v1/recurring-invoices/", body: payload }),
    update: async (id, payload) =>
      request({
        method: "PATCH",
        path: "/api/v1/recurring-invoices/{recurring_id}",
        pathParams: { recurring_id: id },
        body: payload,
      }),
    remove: async (id) =>
      request({
        method: "DELETE",
        path: "/api/v1/recurring-invoices/{recurring_id}",
        pathParams: { recurring_id: id },
      }),
    runNow: async (id) =>
      request({
        method: "POST",
        path: "/api/v1/recurring-invoices/{recurring_id}/run",
        pathParams: { recurring_id: id },
      }),
  },
  dashboard: {
    getMetrics: async ({ months = 12, time_basis = "event_date" } = {}) =>
      request({
        method: "GET",
        path: "/api/v1/dashboard/metrics",
        query: { months, time_basis },
      }),
    getRecentTransactions: async ({ page = 1, page_size = 50 } = {}) =>
      request({
        method: "GET",
        path: "/api/v1/dashboard/recent-transactions",
        query: { page, page_size },
      }),
  },
  notifications: {
    list: async () => request({ method: "GET", path: "/api/v1/notifications/" }),
    markRead: async (notificationId) =>
      request({
        method: "POST",
        path: "/api/v1/notifications/{notification_id}/read",
        pathParams: { notification_id: notificationId },
      }),
  },
  onboarding: {
    getStatus: async () => request({ method: "GET", path: "/api/v1/onboarding/status" }),
    updateStatus: async (payload) => request({ method: "POST", path: "/api/v1/onboarding/status", body: payload }),
    createSampleData: async () => request({ method: "POST", path: "/api/v1/onboarding/sample-data" }),
  },
  feedback: {
    submit: async (payload) => request({ method: "POST", path: "/api/v1/feedback/", body: payload }),
    listMine: async (params = {}) => request({ method: "GET", path: "/api/v1/feedback/", query: params }),
  },
  portal: {
    summary: async (token) =>
      request({
        method: "GET",
        path: "/api/v1/portal/{token}/summary",
        pathParams: { token },
        headers: buildPortalHeaders(token),
      }),
    balance: async (token, params = {}) =>
      request({
        method: "GET",
        path: "/api/v1/portal/{token}/balance",
        pathParams: { token },
        query: params,
        headers: buildPortalHeaders(token),
      }),
    invoices: async (token, params = {}) =>
      request({
        method: "GET",
        path: "/api/v1/portal/{token}/invoices",
        pathParams: { token },
        query: params,
        headers: buildPortalHeaders(token),
      }),
    payments: async (token, params = {}) =>
      request({
        method: "GET",
        path: "/api/v1/portal/{token}/payments",
        pathParams: { token },
        query: params,
        headers: buildPortalHeaders(token),
      }),
    statement: async (token, params = {}) =>
      request({
        method: "GET",
        path: "/api/v1/portal/{token}/statement",
        pathParams: { token },
        query: params,
        headers: buildPortalHeaders(token),
      }),
  },
  ai: {
    overview: async () => request({ method: "GET", path: "/api/v1/ai/overview" }),
    summary: async (params) => request({ method: "GET", path: "/api/v1/ai/summary", query: params }),
    forecast: async (payload) => request({ method: "POST", path: "/api/v1/ai/forecast", body: payload }),
    anomalies: async (payload) => request({ method: "POST", path: "/api/v1/ai/anomaly", body: payload }),
    listLogs: async (params = {}) => request({ method: "GET", path: "/api/v1/ai/logs", query: params }),
    listRuns: async (params = {}) => request({ method: "GET", path: "/api/v1/ai/runs", query: params }),
    getLog: async (id) => request({ method: "GET", path: "/api/v1/ai/logs/{log_id}", pathParams: { log_id: id } }),
    getSummary: async () => request({ method: "GET", path: "/api/v1/ai/summary" }),
    listInsights: async (query = {}) => request({ method: "GET", path: "/api/v1/ai/insights", query }),
    run: async () => request({ method: "POST", path: "/api/v1/ai/run" }),
  },
  ml: {
    latestPrediction: async (prediction_type, model_version) =>
      request({
        method: "GET",
        path: "/api/v1/ml/predictions/latest",
        query: { prediction_type, model_version },
      }),
    exportRevenueSeries: async (params = {}) =>
      request({ method: "GET", path: "/api/v1/ml/exports/revenue_series", query: params }),
    exportTransactions: async (params = {}) =>
      request({ method: "GET", path: "/api/v1/ml/exports/transactions", query: params }),
  },
};
