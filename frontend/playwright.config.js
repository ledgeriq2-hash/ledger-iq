// @ts-check
import { defineConfig } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL || "http://localhost:3000";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60 * 1000,
  use: {
    baseURL,
    headless: true,
  },
  reporter: [["list"]],
});
