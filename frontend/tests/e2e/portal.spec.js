import { test, expect } from "@playwright/test";

const uuid = "11111111-1111-1111-1111-111111111111";

test("smoke nav: dashboard -> predictions -> portal", async ({ page }) => {
  await page.addInitScript(({ tenantId, actorId }) => {
    localStorage.setItem("tenant_id", tenantId);
    localStorage.setItem("actor_id", actorId);
  }, { tenantId: uuid, actorId: uuid });

  await page.route("**/api/settings", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        feature_toggles: {
          ai: true,
          suppliers: true,
          workers: true,
          debts: true,
          invoices: true,
          pages: {
            dashboard_ai: true,
            dashboard_suppliers: true,
            dashboard_workers: true,
            dashboard_debts: true,
            dashboard_invoices: true,
          },
        },
        currency: "USD",
        taxes: { enabled: false, rate: 0 },
        field_labels: {},
        theme: { primary: "#4EB7B3", secondary: "#C1E3E3", mode: "light" },
      }),
    });
  });

  await page.goto("/dashboard");
  await expect(page.getByTestId("dashboard")).toBeVisible();

  await page.getByRole("link", { name: "Predictions" }).click();
  await expect(page.getByTestId("ai-overview")).toBeVisible();
  await expect(page.getByText("AI results will appear here once connected.")).toBeVisible();

  await page.getByRole("link", { name: "Portal" }).click();
  await expect(page.getByText("Portal")).toBeVisible();
  await expect(page.getByText("Missing token")).toBeVisible();
});

