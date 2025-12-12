import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000/api/v1";
const TOKEN = __ENV.TOKEN || "";
const TENANT_ID = __ENV.TENANT_ID || "";

const authHeaders = TOKEN
  ? {
      headers: {
        Authorization: `Bearer ${TOKEN}`,
        "X-Tenant-ID": TENANT_ID,
        "Content-Type": "application/json",
      },
    }
  : { headers: { "Content-Type": "application/json" } };

export function loginScenario() {
  const payload = JSON.stringify({
    email: __ENV.LOGIN_EMAIL || "test@example.com",
    password: __ENV.LOGIN_PASSWORD || "changeme",
    tenant: __ENV.LOGIN_TENANT || "tenant",
  });
  const res = http.post(`${BASE_URL}/auth/login`, payload, { headers: { "Content-Type": "application/json" } });
  check(res, { "login responded": (r) => r.status < 500 });
  sleep(1);
}

export function crudScenario() {
  const customerRes = http.post(
    `${BASE_URL}/customers/`,
    JSON.stringify({ name: `k6-${Date.now()}`, email: "k6@example.com" }),
    authHeaders
  );
  check(customerRes, { "customer created": (r) => r.status === 201 || r.status === 200 });
  const customer = customerRes.json() || {};

  if (customer.id) {
    const invoiceRes = http.post(
      `${BASE_URL}/invoices/`,
      JSON.stringify({
        customer_id: customer.id,
        issue_date: new Date().toISOString().slice(0, 10),
        due_date: new Date().toISOString().slice(0, 10),
        status: "SENT",
        currency: "USD",
        items: [{ description: "Load test", quantity: "1", unit_price: "1.00", tax_rate: "0" }],
      }),
      authHeaders
    );
    check(invoiceRes, { "invoice created": (r) => r.status === 201 || r.status === 200 });

    const paymentRes = http.post(
      `${BASE_URL}/payments/`,
      JSON.stringify({
        customer_id: customer.id,
        invoice_id: invoiceRes.json()?.id,
        amount: "1.00",
        method: "card",
      }),
      authHeaders
    );
    check(paymentRes, { "payment created": (r) => r.status === 201 || r.status === 200 });
  }

  const supplierId =
    __ENV.SUPPLIER_ID ||
    (() => {
      const resp = http.post(
        `${BASE_URL}/suppliers/`,
        JSON.stringify({ name: `k6-supplier-${Date.now()}`, email: "k6@supplier.test", phone: "123" }),
        authHeaders
      );
      return resp.json()?.id;
    })();

  if (supplierId) {
    const expenseRes = http.post(
      `${BASE_URL}/expenses/`,
      JSON.stringify({
        supplier_id: supplierId,
        category: "Ops",
        amount: "1.00",
        currency: "USD",
        expense_date: new Date().toISOString().slice(0, 10),
      }),
      authHeaders
    );
    check(expenseRes, { "expense attempted": (r) => r.status < 500 });
  }
  sleep(1);
}

export function reportsScenario() {
  const res = http.get(`${BASE_URL}/reports/income-statement`, authHeaders);
  check(res, { "reports responded": (r) => r.status < 500 });
  sleep(1);
}

export function portalScenario() {
  const res = http.get(`${BASE_URL}/portal/customer/token`, authHeaders);
  check(res, { "portal responded": (r) => r.status < 500 });
  sleep(1);
}
