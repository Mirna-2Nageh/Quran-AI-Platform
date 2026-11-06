import { expect, test, type Page } from "@playwright/test";

const api = "";
const cors = {
  "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
  "Access-Control-Allow-Credentials": "true",
  "Access-Control-Allow-Headers": "Content-Type, X-CSRF-Token",
  "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
  "Access-Control-Expose-Headers": "X-CSRF-Token",
};

type Plan = {
  id: string;
  surah_number: number;
  start_ayah: number;
  end_ayah: number;
  status: "active" | "completed" | "paused" | "archived";
  created_at: string;
  updated_at: string;
};

type Session = {
  id: string;
  plan_id: string;
  session_type: "memorization" | "revision";
  result: "completed" | "needs_review" | "incomplete";
  notes: string | null;
  completed_at: string;
};

async function setup(page: Page) {
  const plans: Plan[] = [];
  const sessions: Session[] = [];
  const now = "2026-11-04T10:00:00Z";

  await page.route(`${api}/api/v1/auth/me`, route =>
    route.fulfill({
      headers: cors,
      json: {
        id: "e2e-user",
        email: "e2e@example.test",
        full_name: "E2E User",
        role: "student",
        created_at: now,
      },
    }),
  );

  await page.route(`${api}/api/v1/auth/csrf`, route =>
    route.fulfill({
      headers: { ...cors, "X-CSRF-Token": "e2e-token" },
      json: {},
    }),
  );

  await page.route(`${api}/api/v1/memorization/**`, async route => {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname;
    const parts = path.split("/");
    const planId = parts[5];

    if (method === "OPTIONS") {
      await route.fulfill({ status: 204, headers: cors });
      return;
    }

    const respond = (json: unknown, status = 200) =>
      route.fulfill({ status, headers: cors, json });

    if (method !== "GET" &&
        request.headers()["x-csrf-token"] !== "e2e-token") {
      await respond({ detail: "Invalid CSRF token" }, 403);
      return;
    }

    if (path.endsWith("/progress") && method === "GET") {
      const completed = plans.filter(p => p.status === "completed");
      const totalAyahs = plans.reduce(
        (sum, p) => sum + p.end_ayah - p.start_ayah + 1, 0,
      );
      const completedAyahs = completed.reduce(
        (sum, p) => sum + p.end_ayah - p.start_ayah + 1, 0,
      );

      await respond({
        total_plans: plans.length,
        completed_plans: completed.length,
        unique_planned_ayahs: totalAyahs,
        completed_ayahs: completedAyahs,
        completion_rate: totalAyahs
          ? Math.round(completedAyahs / totalAyahs * 100)
          : 0,
        revision_sessions: sessions.filter(
          s => s.session_type === "revision",
        ).length,
      });
      return;
    }

    if (path.endsWith("/plans") && method === "GET") {
      await respond(plans);
      return;
    }

    if (path.endsWith("/plans") && method === "POST") {
      const payload = request.postDataJSON() as Pick<
        Plan, "surah_number" | "start_ayah" | "end_ayah"
      >;
      const plan: Plan = {
        ...payload,
        id: `plan-${plans.length + 1}`,
        status: "active",
        created_at: now,
        updated_at: now,
      };
      plans.push(plan);
      await respond(plan, 201);
      return;
    }

    const plan = plans.find(p => p.id === planId);

    if (!plan) {
      await respond({ detail: "Plan not found" }, 404);
      return;
    }

    if (parts[6] === "sessions") {
      if (method === "GET") {
        await respond(sessions.filter(s => s.plan_id === planId));
        return;
      }

      if (method === "POST") {
        const payload = request.postDataJSON() as Pick<
          Session, "session_type" | "result" | "notes"
        >;
        const session: Session = {
          ...payload,
          id: `session-${sessions.length + 1}`,
          plan_id: planId,
          completed_at: now,
        };
        sessions.push(session);
        await respond(session, 201);
        return;
      }
    }

    if (method === "PATCH") {
      if (plan.status === "archived") {
        await respond({ detail: "Archived plan cannot be modified" }, 409);
        return;
      }
      Object.assign(plan, request.postDataJSON(), { updated_at: now });
      await respond(plan);
      return;
    }

    await respond({ detail: "Not found" }, 404);
  });

  await page.goto("/memorization");
  await expect(
    page.getByRole("heading", { name: "الحفظ والمراجعة", exact: true }),
  ).toBeVisible();
}

test("create plan, complete it, and update progress", async ({ page }) => {
  await setup(page);

  await expect(page.getByText("الخطط المكتملة: 0/0")).toBeVisible();

  const createForm = page.locator("form").first();
  await createForm.getByLabel("رقم السورة").fill("1");
  await createForm.getByLabel("من الآية").fill("1");
  await createForm.getByLabel("إلى الآية").fill("7");
  await createForm.getByRole("button", { name: "إنشاء الخطة" }).click();

  const plan = page.locator("article").filter({
    hasText: "السورة 1 — الآيات 1–7",
  });

  await expect(plan).toBeVisible();
  await expect(page.getByText("الخطط المكتملة: 0/1")).toBeVisible();

  await plan.getByLabel("الحالة").selectOption("completed");

  await expect(page.getByText("الخطط المكتملة: 1/1")).toBeVisible();
  await expect(page.getByText("نسبة الإنجاز: 100%")).toBeVisible();
});

test("record a revision session and update statistics", async ({ page }) => {
  await setup(page);

  await page.getByRole("button", { name: "إنشاء الخطة" }).click();

  const plan = page.locator("article").first();
  await expect(plan).toBeVisible();

  await plan.getByRole("button", { name: "عرض الجلسات" }).click();

  await expect(
    page.getByText("لا توجد جلسات مسجلة بعد."),
  ).toBeVisible();

  await page.getByLabel("نوع الجلسة").selectOption("revision");
  await page.getByLabel("النتيجة").selectOption("needs_review");
  await page.getByLabel("ملاحظات").fill("مراجعة سورة الفاتحة");

  await page.getByRole("button", { name: "حفظ الجلسة" }).click();

  await expect(page.getByText("جلسات المراجعة: 1")).toBeVisible();
  await expect(page.getByText("مراجعة سورة الفاتحة")).toBeVisible();
});

test("edit plan range and archive it", async ({ page }) => {
  await setup(page);

  await page.getByRole("button", { name: "إنشاء الخطة" }).click();

  const plan = page.locator("article").first();
  await expect(plan).toBeVisible();

  await plan.getByRole("button", { name: "تعديل الخطة" }).click();

  const editForm = plan.locator("form");
  await editForm.getByLabel("من الآية").fill("2");
  await editForm.getByLabel("إلى الآية").fill("5");
  await editForm.getByRole("button", { name: "حفظ التعديلات" }).click();

  await expect(plan).toContainText("الآيات 2–5");
  await expect(page.getByText("الآيات المكتملة: 0/4")).toBeVisible();

  page.once("dialog", dialog => dialog.accept());
  await plan.getByLabel("الحالة").selectOption("archived");

  await expect(plan.getByLabel("الحالة")).toHaveValue("archived");
  await expect(
    plan.getByRole("button", { name: "تعديل الخطة" }),
  ).toHaveCount(0);

  await plan.getByRole("button", { name: "عرض الجلسات" }).click();

  await expect(page.getByText(
    "هذه الخطة مؤرشفة. يمكنك مراجعة جلساتها السابقة فقط.",
  )).toBeVisible();

  await expect(
    page.getByRole("button", { name: "حفظ الجلسة" }),
  ).toHaveCount(0);
});

test("cancel archive confirmation keeps plan active", async ({ page }) => {
  await setup(page);

  await page.getByRole("button", { name: "إنشاء الخطة" }).click();

  const plan = page.locator("article").first();
  await expect(plan).toBeVisible();

  page.once("dialog", dialog => dialog.dismiss());
  await plan.getByLabel("الحالة").selectOption("archived");

  await expect(plan.getByLabel("الحالة")).toHaveValue("active");
  await expect(
    plan.getByRole("button", { name: "تعديل الخطة" }),
  ).toBeVisible();
});

test("shows API error when plan creation fails", async ({ page }) => {
  await setup(page);

  await page.route(
    `${api}/api/v1/memorization/plans`,
    async route => {
      if (route.request().method() !== "POST") {
        await route.fallback();
        return;
      }

      await route.fulfill({
        status: 422,
        headers: cors,
        json: { detail: "Invalid Quran range" },
      });
    },
  );

  await page.getByRole("button", { name: "إنشاء الخطة" }).click();

  await expect(
    page.getByRole("alert"),
  ).toContainText("Invalid Quran range");

  await expect(
    page.getByText("لا توجد خطط حفظ بعد."),
  ).toBeVisible();

  await expect(
    page.getByText("الخطط المكتملة: 0/0"),
  ).toBeVisible();
});
