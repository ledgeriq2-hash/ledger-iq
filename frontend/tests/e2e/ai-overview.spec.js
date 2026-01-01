import { test, expect } from "@playwright/test";
import { loginViaUI, registerUser } from "./utils.js";

test("AI overview renders", async ({ page, request }) => {
  const user = await registerUser(request);
  await loginViaUI(page, user);
  await page.goto("/predictions");
  await expect(page.getByTestId("ai-overview")).toBeVisible();
  await expect(page.getByText("AI Overview")).toBeVisible();
  await expect(page.getByText("AI results will appear here once connected.")).toBeVisible();
});
