import { randomUUID } from "crypto";

const apiBase = process.env.API_BASE_URL || "http://localhost:8000/api/v1";

export const registerUser = async (request) => {
  const slug = `tenant-${randomUUID().slice(0, 8)}`;
  const email = `${slug}@example.com`;
  const password = "Test123!";
  const res = await request.post(`${apiBase}/auth/register`, {
    data: {
      tenant: { name: `Tenant ${slug}`, slug },
      admin: { email, password, full_name: "E2E User" },
    },
  });
  if (!res.ok()) throw new Error(`Failed to register: ${res.status()}`);
  const body = await res.json();
  const accessToken = body?.tokens?.access_token || body?.access_token;
  const refreshToken = body?.tokens?.refresh_token || body?.refresh_token;
  const tenantId = body?.tenant?.id || body?.tenant_id;
  return { slug, email, password, tenantId, accessToken, refreshToken };
};

export const authHeaders = (token, tenantId) => ({
  Authorization: `Bearer ${token}`,
  "X-Tenant-ID": tenantId,
});

export const loginViaUI = async (page, creds) => {
  await page.goto("/login");
  await page.getByTestId("input-tenant").fill(creds.slug);
  await page.getByTestId("input-email").fill(creds.email);
  await page.getByTestId("input-password").fill(creds.password);
  await page.getByTestId("btn-login").click();
};

export const seedCustomerInvoicePayment = async (request, headers) => {
  const customerRes = await request.post(`${apiBase}/customers/`, {
    data: { name: "E2E Customer", email: "customer@example.com" },
    headers,
  });
  const customer = await customerRes.json();
  const invoiceRes = await request.post(`${apiBase}/invoices/`, {
    data: {
      customer_id: customer.id,
      issue_date: new Date().toISOString().slice(0, 10),
      due_date: new Date().toISOString().slice(0, 10),
      status: "PAID",
      currency: "USD",
      items: [{ description: "Item", quantity: "1", unit_price: "10.00", tax_rate: "0" }],
    },
    headers,
  });
  const invoice = await invoiceRes.json();
  await request.post(`${apiBase}/payments/`, {
    data: { invoice_id: invoice.id, customer_id: customer.id, amount: "10.00", method: "card" },
    headers,
  });
  return { customer, invoice };
};

export const seedSupplierExpense = async (request, headers) => {
  const supplierRes = await request.post(`${apiBase}/suppliers/`, {
    data: { name: "E2E Vendor", email: "vendor@example.com", phone: "555-0001" },
    headers,
  });
  const supplier = await supplierRes.json();
  await request.post(`${apiBase}/expenses/`, {
    data: {
      supplier_id: supplier.id,
      category: "Services",
      amount: "12.00",
      currency: "USD",
      expense_date: new Date().toISOString().slice(0, 10),
      description: "E2E Expense",
    },
    headers,
  });
  return { supplier };
};
