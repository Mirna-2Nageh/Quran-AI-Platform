import { expect, test, type Page } from "@playwright/test";

const api = "";
const cors = {
  "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
  "Access-Control-Allow-Credentials": "true",
  "Access-Control-Allow-Headers": "Content-Type, X-CSRF-Token",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Expose-Headers": "X-CSRF-Token",
};

const halaqa = {
  id: "halaqa-1",
  name: "حلقة الفاتحة",
  description: "حفظ ومراجعة",
  teacher_id: "teacher-1",
  status: "active",
  created_at: "2026-11-04T10:00:00Z",
  updated_at: "2026-11-04T10:00:00Z",
};

const student = {
  id: "enrollment-1",
  halaqa_id: "halaqa-1",
  student_id: "student-1",
  student_name: "محمد علي",
  halaqa_name: "حلقة الفاتحة",
  status: "active",
  created_at: "2026-11-04T10:00:00Z",
};

async function setup(page: Page, role = "teacher") {
  let sessions: Array<Record<string, unknown>> = [];

  await page.route(`${api}/api/v1/**`, route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();

    if (method === "OPTIONS") {
      return route.fulfill({ status: 204, headers: cors });
    }

    const respond = (data: unknown, status = 200) =>
      route.fulfill({ status, headers: cors, json: data });

    if (path === "/api/v1/auth/me") {
      return respond({
        id: "teacher-1",
        full_name: "أحمد محمد",
        email: "teacher@example.test",
        role,
        created_at: "2026-01-01T00:00:00Z",
      });
    }

    if (path === "/api/v1/auth/csrf") {
      return route.fulfill({
        headers: { ...cors, "X-CSRF-Token": "e2e-token" },
        json: { csrf_token: "e2e-token" },
      });
    }

    if (path === "/api/v1/halaqat/my") {
      return respond([halaqa]);
    }

    if (path === "/api/v1/halaqat/halaqa-1") {
      return respond(halaqa);
    }

    if (path === "/api/v1/halaqat/halaqa-1/enrollments") {
      return respond([student]);
    }

    if (path === "/api/v1/halaqat/halaqa-1/sessions") {
      if (method === "GET") return respond(sessions);

      if (method === "POST") {
        const body = request.postDataJSON();
        const created = {
          id: "session-1",
          halaqa_id: "halaqa-1",
          ...body,
          status: "scheduled",
          created_at: "2026-11-04T10:00:00Z",
          updated_at: "2026-11-04T10:00:00Z",
        };
        sessions = [...sessions, created];
        return respond(created, 201);
      }
    }

    if (path.includes("/attendance")) {
      return respond([]);
    }

    return respond({ detail: `Unmocked: ${method} ${path}` }, 404);
  });

  return { getSessions: () => sessions };
}

test("teacher sees assigned halaqat", async ({ page }) => {
  await setup(page);
  await page.goto("/halaqat/teacher");

  await expect(page.getByRole("heading", {
    name: "حلقاتي التعليمية",
  })).toBeVisible();

  await expect(page.getByRole("link", {
    name: /حلقة الفاتحة/,
  })).toBeVisible();
});

test("teacher opens halaqa and sees enrolled students", async ({ page }) => {
  await setup(page);
  await page.goto("/halaqat/teacher");

  await page.getByRole("link", { name: /حلقة الفاتحة/ }).click();

  await expect(page).toHaveURL(/\/halaqat\/teacher\/halaqa-1$/);
  await expect(page.getByRole("heading", {
    name: "الطلاب المسجلون (1)",
  })).toBeVisible();

  await expect(page.getByText("الطالب: محمد علي")).toBeVisible();
});

test("teacher creates a halaqa session", async ({ page }) => {
  const mock = await setup(page);
  await page.goto("/halaqat/teacher/halaqa-1");

  const future = new Date(Date.now() + 7 * 86400000);
  const local = new Date(
    future.getTime() - future.getTimezoneOffset() * 60000,
  ).toISOString().slice(0, 16);

  await page.locator("#halaqa-scheduled-at").fill(local);
  await page.locator("#halaqa-duration").fill("45");
  await page.locator("#halaqa-notes").fill("مراجعة سورة الفاتحة");

  await page.getByRole("button", { name: "إنشاء الجلسة" }).click();

  await expect(page.getByText("تم إنشاء الجلسة بنجاح."))
    .toBeVisible();

  await expect(page.getByRole("heading", {
    name: "الجلسات (1)",
  })).toBeVisible();

  expect(mock.getSessions()).toHaveLength(1);
  expect(mock.getSessions()[0].duration_minutes).toBe(45);
});

test("teacher sees error when halaqat API fails", async ({ page }) => {
  await setup(page);

  await page.route(`${api}/api/v1/halaqat/my`, route =>
    route.fulfill({
      status: 503,
      headers: cors,
      json: { detail: "Halaqat service unavailable" },
    }),
  );

  await page.goto("/halaqat/teacher");

  await expect(page.getByRole("alert"))
    .toContainText("Halaqat service unavailable");
});

test("student cannot access teacher halaqat", async ({ page }) => {
  await setup(page, "student");
  await page.goto("/halaqat/teacher");

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", {
    name: "حلقاتي التعليمية",
  })).toHaveCount(0);
});
