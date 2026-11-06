import { expect, test, type Page } from "@playwright/test";

const api = "";
const cors = {
  "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
  "Access-Control-Allow-Credentials": "true",
  "Access-Control-Allow-Headers": "Content-Type, X-CSRF-Token",
  "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
  "Access-Control-Expose-Headers": "X-CSRF-Token",
};

const now = "2026-11-04T10:00:00Z";

async function setup(page: Page, future = false, fail = false) {
  let savedStatus = "";

  await page.route(`${api}/api/v1/**`, route => {
    const req = route.request();
    const path = new URL(req.url()).pathname;
    const method = req.method();

    if (method === "OPTIONS") {
      return route.fulfill({ status: 204, headers: cors });
    }

    const respond = (data: unknown, status = 200) =>
      route.fulfill({ status, headers: cors, json: data });

    if (path === "/api/v1/auth/me") {
      return respond({
        id: "teacher-1", role: "teacher",
        full_name: "أحمد محمد",
        email: "teacher@example.test",
        created_at: now,
      });
    }

    if (path === "/api/v1/auth/csrf") {
      return route.fulfill({
        headers: { ...cors, "X-CSRF-Token": "e2e-token" },
        json: { csrf_token: "e2e-token" },
      });
    }

    if (path === "/api/v1/halaqat/halaqa-1") {
      return respond({
        id: "halaqa-1", name: "حلقة الفاتحة",
        description: "حفظ ومراجعة",
        teacher_id: "teacher-1", status: "active",
        created_at: now, updated_at: now,
      });
    }

    if (path === "/api/v1/halaqat/halaqa-1/enrollments") {
      return respond([{
        id: "enrollment-1", halaqa_id: "halaqa-1",
        student_id: "student-1",
        student_name: "محمد علي",
        halaqa_name: "حلقة الفاتحة",
        status: "active", created_at: now,
      }]);
    }

    if (path === "/api/v1/halaqat/halaqa-1/sessions") {
      return respond([{
        id: "session-1", halaqa_id: "halaqa-1",
        scheduled_at: future
          ? new Date(Date.now() + 86400000).toISOString()
          : new Date(Date.now() - 86400000).toISOString(),
        duration_minutes: 60,
        notes: null, status: "scheduled",
        created_at: now, updated_at: now,
      }]);
    }

    if (path === "/api/v1/halaqat/sessions/session-1/attendance") {
      if (method === "GET") return respond([]);

      if (method === "PUT") {
        if (fail) {
          return respond({ detail: "Attendance unavailable" }, 503);
        }

        const body = req.postDataJSON();
        savedStatus = body.status;

        return respond({
          id: "attendance-1", session_id: "session-1",
          student_id: body.student_id,
          status: body.status, notes: null,
          recorded_by: "teacher-1",
          halaqa_name: "حلقة الفاتحة",
          session_scheduled_at: now,
          created_at: now, updated_at: now,
        });
      }
    }

    return respond({ detail: `Unmocked: ${method} ${path}` }, 404);
  });

  return { getSavedStatus: () => savedStatus };
}

test("teacher records student attendance", async ({ page }) => {
  const mock = await setup(page);
  await page.goto("/halaqat/teacher/halaqa-1");

  const select = page.getByRole("combobox", {
    name: "حضور الطالب محمد علي",
  });

  await expect(select).toBeEnabled();
  await select.selectOption("present");

  await expect(select).toHaveValue("present");
  expect(mock.getSavedStatus()).toBe("present");
});

test("attendance is disabled before session starts", async ({ page }) => {
  const mock = await setup(page, true);
  await page.goto("/halaqat/teacher/halaqa-1");

  const select = page.getByRole("combobox", {
    name: "حضور الطالب محمد علي",
  });

  await expect(select).toBeDisabled();
  await expect(page.getByText(
    /تسجيل الحضور غير متاح قبل بدء الجلسة/,
  )).toBeVisible();

  expect(mock.getSavedStatus()).toBe("");
});

test("teacher sees attendance API error", async ({ page }) => {
  await setup(page, false, true);
  await page.goto("/halaqat/teacher/halaqa-1");

  const select = page.getByRole("combobox", {
    name: "حضور الطالب محمد علي",
  });

  await expect(select).toBeEnabled();
  await select.selectOption("absent");

  await expect(page.getByRole("alert"))
    .toContainText("Attendance unavailable");

  await expect(select).toHaveValue("");
});
