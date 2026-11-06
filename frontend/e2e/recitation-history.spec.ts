import { expect, test, type Page } from "@playwright/test";

const api = "";
const cors = {
  "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
  "Access-Control-Allow-Credentials": "true",
};

const sample = {
  id: "history-1",
  surah_number: 1,
  ayah_number: 1,
  end_ayah_number: 1,
  expected_text: "بسم الله الرحمن الرحيم",
  recognized_text: "بسم الله الرحيم",
  alignment: {
    expected_word_count: 4,
    recognized_word_count: 3,
    matched_word_count: 3,
    issues: [{
      operation: "deletion",
      expected_word: "الرحمن",
      recognized_word: null,
      expected_index: 2,
      recognized_index: null,
    }],
  },
  analysis_type: "word_level_asr_alignment",
  tajweed_analyzed: false,
  created_at: "2026-11-04T10:00:00Z",
};

async function setup(
  page: Page,
  initialItems: typeof sample[] = [],
) {
  let items = [...initialItems];

  await page.route(`${api}/api/v1/auth/me`, route =>
    route.fulfill({
      headers: cors,
      json: {
        id: "e2e-user",
        email: "e2e@example.test",
        full_name: "E2E User",
        role: "student",
        created_at: "2026-01-01T00:00:00Z",
      },
    }),
  );

  await page.route("https://api.alquran.cloud/v1/surah", route =>
    route.fulfill({
      json: {
        code: 200,
        data: [{
          number: 1,
          name: "الفاتحة",
          englishName: "Al-Faatiha",
          numberOfAyahs: 7,
          revelationType: "Meccan",
        }],
      },
    }),
  );

  await page.route(
    `${api}/api/v1/recitation/history?limit=20`,
    route => route.fulfill({
      headers: cors,
      json: {
        items,
        count: items.length,
        has_more: false,
        next_cursor: null,
      },
    }),
  );

  return {
    setItems(nextItems: typeof sample[]) {
      items = [...nextItems];
    },
  };
}

test("shows saved recitation and word statistics", async ({ page }) => {
  await setup(page, [sample]);
  await page.goto("/recitation/history");

  await expect(
    page.getByRole("heading", { name: "سجل التلاوات" }),
  ).toBeVisible();

  const entry = page.locator("article.recitation-panel");
  await expect(entry).toHaveCount(1);
  await expect(entry).toContainText("الفاتحة");
  await expect(entry).toContainText("الآية 1");
  await expect(entry).toContainText("كلمات متطابقة");
  await expect(entry).toContainText("اختلافات نصية");
});

test("opens details and shows word-level differences", async ({ page }) => {
  await setup(page, [sample]);
  await page.goto("/recitation/history");

  const entry = page.locator("article.recitation-panel");
  await entry.locator("summary").click();

  await expect(entry.getByText("النص المتوقع")).toBeVisible();
  await expect(entry.getByText(sample.expected_text, { exact: true }))
    .toBeVisible();
  await expect(entry.getByText(sample.recognized_text, { exact: true }))
    .toBeVisible();

  await expect(entry.getByText("كلمة ناقصة")).toBeVisible();
  await expect(entry.getByText("المتوقع: الرحمن")).toBeVisible();
});

test("shows empty state when history is empty", async ({ page }) => {
  await setup(page);
  await page.goto("/recitation/history");

  await expect(
    page.getByRole("heading", { name: "لا توجد تلاوات محفوظة بعد" }),
  ).toBeVisible();

  await expect(
    page.getByRole("link", { name: "ابدأ التلاوة" }),
  ).toHaveAttribute("href", "/recitation");
});

test("shows API error when history request fails", async ({ page }) => {
  await setup(page);

  await page.route(
    `${api}/api/v1/recitation/history?limit=20`,
    route => route.fulfill({
      status: 503,
      headers: cors,
      json: { detail: "History service unavailable" },
    }),
  );

  await page.goto("/recitation/history");

  await expect(page.getByRole("alert"))
    .toContainText("History service unavailable");

  await expect(
    page.getByRole("heading", { name: "لا توجد تلاوات محفوظة بعد" }),
  ).toHaveCount(0);
});

test("refresh loads newly saved recitations", async ({ page }) => {
  const mock = await setup(page);
  await page.goto("/recitation/history");

  await expect(
    page.getByRole("heading", { name: "لا توجد تلاوات محفوظة بعد" }),
  ).toBeVisible();

  mock.setItems([sample]);

  await page.getByRole("button", { name: "تحديث السجل" }).click();

  await expect(
    page.locator("article.recitation-panel"),
  ).toHaveCount(1);

  await expect(
    page.getByRole("heading", { name: /الآية 1/ }),
  ).toBeVisible();
});
