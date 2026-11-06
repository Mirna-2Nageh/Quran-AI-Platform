import { test, expect, type Page } from "@playwright/test";

const api = "";

const surah = {
  number: 1,
  name: "سُورَةُ ٱلْفَاتِحَةِ",
  englishName: "Al-Faatiha",
  numberOfAyahs: 1,
  revelationType: "Meccan",
};

async function mockQuran(page: Page) {
  await page.route(`${api}/api/v1/auth/me`, (route) =>
    route.fulfill({
      json: {
        id: "e2e-user",
        email: "e2e@example.test",
        full_name: "E2E User",
        role: "student",
        created_at: "2026-01-01T00:00:00Z",
      },
    }),
  );

  await page.route(`${api}/api/v1/quran/**`, (route) => {
    const path = new URL(route.request().url()).pathname;

    if (path.endsWith("/bookmarks")) {
      return route.fulfill({ json: { items: [], count: 0 } });
    }

    if (path.endsWith("/progress")) {
      return route.fulfill({ json: null });
    }

    return route.fulfill({ status: 404 });
  });

  await page.route("https://api.alquran.cloud/v1/**", (route) => {
    const path = new URL(route.request().url()).pathname;

    if (path === "/v1/surah") {
      return route.fulfill({
        json: {
          code: 200,
          data: [
            surah,
            { ...surah, number: 2, name: "سُورَةُ الْبَقَرَةِ", englishName: "Al-Baqara" },
          ],
        },
      });
    }

    if (path === "/v1/surah/1/ar.uthmani") {
      return route.fulfill({
        json: {
          code: 200,
          data: {
            ...surah,
            ayahs: [{
              number: 1,
              numberInSurah: 1,
              text: "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
            }],
          },
        },
      });
    }

    if (path === "/v1/ayah/1:1/ar.muyassar") {
      return route.fulfill({
        json: {
          code: 200,
          data: {
            numberInSurah: 1,
            text: "أبدأ قراءة القرآن باسم الله.",
            edition: {
              identifier: "ar.muyassar",
              name: "التفسير الميسر",
            },
          },
        },
      });
    }

    return route.fulfill({ status: 404 });
  });
}

test("unauthenticated user is redirected to login", async ({ page }) => {
  await page.route(`${api}/api/v1/auth/me`, (route) =>
    route.fulfill({ status: 401, json: { detail: "Unauthorized" } }),
  );

  await page.goto("/quran");
  await expect(page).toHaveURL(/\/login$/);
});

test("authenticated user can browse and search surahs", async ({ page }) => {
  await mockQuran(page);
  await page.goto("/quran");

  await expect(page.getByRole("heading", { name: "فهرس السور" })).toBeVisible();

  await expect(page.locator(".surah-card")).toHaveCount(2);

  await page.getByPlaceholder("ابحث باسم السورة أو رقمها...").fill("2");

  await expect(page.locator(".surah-card")).toHaveCount(1);
  await expect(page.locator(".surah-card")).toContainText("Al-Baqara");
});

test("user can open a surah and view tafsir", async ({ page }) => {
  await mockQuran(page);
  await page.goto("/quran");

  await page.locator(".surah-card").first().click();

  await expect(page).toHaveURL(/\/quran\/1$/);

  await expect(page.locator(".ayah-text")).toContainText("بِسْمِ");

  await page.getByRole("button", { name: "عرض التفسير" }).click();

  await expect(page.getByRole("region", { name: "تفسير الآية" }))
    .toContainText("أبدأ قراءة القرآن باسم الله.");
});
