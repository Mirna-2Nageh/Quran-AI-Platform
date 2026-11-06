import { expect, test } from "@playwright/test";

test("CSRF requests share one refresh and reuse cached token", async ({ page }) => {
  let refreshCount = 0;

  await page.route("**/api/v1/auth/csrf", async route => {
    refreshCount += 1;
    await new Promise(resolve => setTimeout(resolve, 150));

    await route.fulfill({
      status: 200,
      headers: { "X-CSRF-Token": `token-${refreshCount}` },
      json: {},
    });
  });

  await page.goto("/");

  const result = await page.evaluate(async () => {
    const auth = await import("/src/features/auth/api/auth.ts");

    const [first, second] = await Promise.all([
      auth.getCsrfToken(),
      auth.getCsrfToken(),
    ]);

    const third = await auth.getCsrfToken();

    await auth.refreshCsrf();
    const fourth = await auth.getCsrfToken();

    return { first, second, third, fourth };
  });

  expect(refreshCount).toBe(2);
  expect(result.first).toBe("token-1");
  expect(result.second).toBe("token-1");
  expect(result.third).toBe("token-1");
  expect(result.fourth).toBe("token-2");
});
