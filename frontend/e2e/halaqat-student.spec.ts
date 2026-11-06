import { expect, test, type Page } from "@playwright/test";

const api = "";
const cors = {
  "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
  "Access-Control-Allow-Credentials": "true",
  "Access-Control-Allow-Headers": "Content-Type, X-CSRF-Token",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
};

const created = "2026-11-04T10:00:00Z";

async function setup(
  page: Page,
  options: { role?: string; empty?: boolean; fail?: boolean } = {},
) {
  const { role = "student", empty = false, fail = false } = options;

  await page.route(`${api}/api/v1/**`, route => {
    const req = route.request();
    const path = new URL(req.url()).pathname;

    if (req.method() === "OPTIONS") {
      return route.fulfill({ status: 204, headers: cors });
    }

    const respond = (data: unknown, status = 200) =>
      route.fulfill({ status, headers: cors, json: data });

    if (path === "/api/v1/auth/me") {
      return respond({
        id: "student-1",
        full_name: "محمد علي",
        email: "student@example.test",
        role,
        created_at: created,
      });
    }

    if (path === "/api/v1/halaqat/my/enrollments") {
      if (fail) return respond({ detail: "Enrollment service unavailable" }, 503);
      return respond(empty ? [] : [{
        id: "enrollment-1",
        halaqa_id: "halaqa-1",
        student_id: "student-1",
        student_name: "محمد علي",
        halaqa_name: "حلقة الفاتحة",
        status: "active",
        created_at: created,
      }]);
    }

    if (path === "/api/v1/halaqat/my/attendance") {
      return respond(empty ? [] : [{
        id: "attendance-1",
        session_id: "session-1",
        student_id: "student-1",
        status: "present",
        notes: "مراجعة ممتازة",
        recorded_by: "teacher-1",
        halaqa_name: "حلقة الفاتحة",
        session_scheduled_at: created,
        created_at: created,
        updated_at: created,
      }]);
    }

    return respond({ detail: `Unmocked: ${path}` }, 404);
  });
}

test("student sees enrolled halaqat and attendance", async ({ page }) => {
  await setup(page);
  await page.goto("/halaqat/student");

  await expect(page.getByRole("heading", {
    name: "الحلقات المسجل بها (1)",
  })).toBeVisible();

  await expect(page.getByRole("heading", {
    name: "سجل الحضور (1)",
  })).toBeVisible();

  await expect(page.getByText("حالة التسجيل: نشط")).toBeVisible();
  await expect(page.getByText("حالة الحضور: حاضر")).toBeVisible();
  await expect(page.getByText("مراجعة ممتازة")).toBeVisible();
});

test("student sees empty state", async ({ page }) => {
  await setup(page, { empty: true });
  await page.goto("/halaqat/student");

  await expect(page.getByText(
    "لم يتم تسجيلك في أي حلقة بعد.",
  )).toBeVisible();

  await expect(page.getByText(
    "لا يوجد سجل حضور حتى الآن.",
  )).toBeVisible();
});

test("student sees API error", async ({ page }) => {
  await setup(page, { fail: true });
  await page.goto("/halaqat/student");

  await expect(page.getByRole("alert"))
    .toContainText("Enrollment service unavailable");
});

test("teacher cannot access student halaqat", async ({ page }) => {
  await setup(page, { role: "teacher" });
  await page.goto("/halaqat/student");

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", {
    name: "حلقاتي الدراسية",
  })).toHaveCount(0);
});
