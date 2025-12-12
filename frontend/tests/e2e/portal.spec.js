import { test, expect } from "@playwright/test";
import { authHeaders, loginViaUI, registerUser, seedCustomerInvoicePayment, seedSupplierExpense } from "./utils.js";

const apiBase = process.env.API_BASE_URL || "http://localhost:8000/api/v1";

test("customer portal readability", async ({ page, request }) => {
  const user = await registerUser(request);
  const headers = authHeaders(user.accessToken, user.tenantId);
  const { customer } = await seedCustomerInvoicePayment(request, headers);

  const tokenRes = await request.post(`${apiBase}/portal/customer/token`, {
    data: { customer_id: customer.id },
    headers,
  });
  const tokenData = await tokenRes.json();
  const portalUrl = tokenData.url || tokenData.message || "";
  const rawToken = portalUrl.split("/").pop();

  await page.goto(`/portal/customer/${rawToken}`);
  await expect(page.getByTestId("customer-portal")).toBeVisible();
});

test("supplier portal readability", async ({ page, request }) => {
  const user = await registerUser(request);
  const headers = authHeaders(user.accessToken, user.tenantId);
  const { supplier } = await seedSupplierExpense(request, headers);

  const tokenRes = await request.post(`${apiBase}/portal/supplier/token`, {
    data: { supplier_id: supplier.id },
    headers,
  });
  const tokenData = await tokenRes.json();
  const rawToken = (tokenData.url || "").split("/").pop();

  await page.goto(`/portal/supplier/${rawToken}`);
  await expect(page.getByTestId("supplier-portal")).toBeVisible();
});

test("create customer > invoice > payment via UI/API mix", async ({ page, request }) => {
  const user = await registerUser(request);
  await loginViaUI(page, user);

  await page.goto("/customers");
  await page.getByTestId("customer-name").fill("UI Customer");
  await page.getByTestId("customer-email").fill("ui@example.com");
  await page.getByTestId("customer-submit").click();
  await expect(page.getByText("Customers")).toBeVisible();

  await page.goto("/invoices");
  await page.getByTestId("invoice-customer").selectOption({ index: 1 });
  const today = new Date().toISOString().slice(0, 10);
  await page.getByTestId("invoice-issue-date").fill(today);
  await page.getByTestId("invoice-due-date").fill(today);
  await page.getByTestId("invoice-total").fill("25");
  await page.getByTestId("invoice-submit").click();
  await expect(page.getByText("Invoices")).toBeVisible();

  // Payment via API (no UI form)
  const headers = authHeaders(user.accessToken, user.tenantId);
  const invoicesRes = await request.get(`${apiBase}/invoices/`, { headers });
  const invoiceList = await invoicesRes.json();
  const invoiceId = invoiceList?.items?.[0]?.id || invoiceList?.[0]?.id;
  const customersRes = await request.get(`${apiBase}/customers/`, { headers });
  const customerList = await customersRes.json();
  const customerId = customerList?.items?.[0]?.id || customerList?.[0]?.id;
  await request.post(`${apiBase}/payments/`, {
    data: { customer_id: customerId, invoice_id: invoiceId, amount: "25.00", method: "card" },
    headers,
  });
});
