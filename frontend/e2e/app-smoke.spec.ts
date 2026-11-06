import { test, expect } from "@playwright/test";

test("React application loads successfully", async ({ page }) => {
  const errors: string[] = [];

  page.on("pageerror", (error) => {
    errors.push(error.message);
  });

  await page.goto("/");

  await expect(page.locator("#root")).toBeVisible();

  expect(errors).toEqual([]);
});
