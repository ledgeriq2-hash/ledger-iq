import { test, expect } from "@playwright/test";
import { registerUser, loginViaUI } from "./utils.js";

test("login and logout flow", async ({ page, request }) => {
  const user = await registerUser(request);
  await loginViaUI(page, user);
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText("Dashboard")).toBeVisible();

  await page.getByTestId("btn-logout").click();
  await expect(page).toHaveURL(/login/);
});
