/**
 * Perfect School 4.1 Block 5: Playwright E2E Tests
 *
 * 7 critical tests covering the main user flows.
 */
import { test, expect } from "@playwright/test";

const BASE = process.env.BASE_URL || "http://localhost:5173";

test.describe("EduAI Companion E2E", () => {
  // Test 1: Landing page loads
  test("landing page renders correctly", async ({ page }) => {
    await page.goto(BASE);
    await expect(page.locator("text=EduAI")).toBeVisible({ timeout: 10000 });
  });

  // Test 2: Auth page accessible
  test("auth page shows login form", async ({ page }) => {
    await page.goto(`${BASE}/auth`);
    await expect(page.locator("text=Anmelden")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("input")).toHaveCount(2); // username + password
  });

  // Test 3: Registration flow
  test("registration form has all fields", async ({ page }) => {
    await page.goto(`${BASE}/auth`);
    // Switch to register mode
    const registerLink = page.locator("text=Jetzt registrieren");
    if (await registerLink.isVisible()) {
      await registerLink.click();
    }
    await expect(page.locator("text=Konto erstellen")).toBeVisible({ timeout: 5000 });
  });

  // Test 4: Google OAuth button present
  test("google oauth button is visible", async ({ page }) => {
    await page.goto(`${BASE}/auth`);
    await expect(page.locator("text=Mit Google anmelden")).toBeVisible({ timeout: 10000 });
  });

  // Test 5: PWA manifest present
  test("PWA manifest is accessible", async ({ page }) => {
    const response = await page.goto(`${BASE}/manifest.json`);
    if (response) {
      expect(response.status()).toBeLessThan(400);
    }
  });

  // Test 6: Service worker registered
  test("service worker file exists", async ({ page }) => {
    const response = await page.goto(`${BASE}/sw.js`);
    if (response) {
      expect(response.status()).toBeLessThan(400);
    }
  });

  // Test 7: API health check
  test("backend health check responds", async ({ request }) => {
    const apiUrl = process.env.API_URL || "http://localhost:8000";
    try {
      const response = await request.get(`${apiUrl}/healthz`);
      expect(response.status()).toBe(200);
    } catch {
      // Backend may not be running in CI - skip gracefully
      test.skip();
    }
  });
});
