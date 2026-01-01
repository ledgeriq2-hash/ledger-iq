import { test, expect } from "@playwright/test";

test("dashboard loads without auth", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByText("Dashboard")).toBeVisible();
});
