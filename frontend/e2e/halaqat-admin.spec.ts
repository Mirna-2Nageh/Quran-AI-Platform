import { expect, test, type Page } from "@playwright/test";

const api = "";
const cors = {
  "Access-Control-Allow-Origin": "http://127.0.0.1:5173",
  "Access-Control-Allow-Credentials": "true",
  "Access-Control-Allow-Headers": "Content-Type, X-CSRF-Token",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Expose-Headers": "X-CSRF-Token",
};

const teacher = {
  id: "teacher-1", full_name: "أحمد محمد",
  email: "teacher@example.test", role: "teacher",
};
const student = {
  id: "student-1", full_name: "محمد علي",
  email: "student@example.test", role: "student",
};
const halaqa = {
  id: "halaqa-1", name: "حلقة الفاتحة",
  description: "حفظ ومراجعة", teacher_id: teacher.id,
  status: "active",
  created_at: "2026-11-04T10:00:00Z",
  updated_at: "2026-11-04T10:00:00Z",
};

async function setup(page: Page, role = "admin") {
  let teachers = [teacher];
  let halaqat: typeof halaqa[] = [];
  let enrollments: Array<Record<string, unknown>> = [];

  await page.route(`${api}/api/v1/**`, async route => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;
    const method = request.method();

    if (method === "OPTIONS") {
      return route.fulfill({ status: 204, headers: cors });
    }

    const respond = (data: unknown, status = 200) =>
      route.fulfill({ status, headers: cors, json: data });

    if (path === "/api/v1/auth/me") {
      return respond({
        id: "e2e-admin", full_name: "E2E Admin",
        email: "admin@example.test", role,
        created_at: "2026-01-01T00:00:00Z",
      });
    }
    if (path === "/api/v1/auth/csrf") {
      return route.fulfill({
        headers: { ...cors, "X-CSRF-Token": "e2e-token" },
        json: { csrf_token: "e2e-token" },
      });
    }
    if (path === "/api/v1/admin/users" && method === "GET") {
      return respond(url.searchParams.get("role") === "teacher"
        ? teachers : [student]);
    }
    if (path === "/api/v1/admin/users" && method === "POST") {
      const body = request.postDataJSON();
      const created = {
        id: "teacher-2", full_name: body.full_name,
        email: body.email, role: "teacher",
      };
      teachers = [...teachers, created];
      return respond(created, 201);
    }
    if (path === "/api/v1/halaqat" && method === "GET") {
      return respond(halaqat);
    }
    if (path === "/api/v1/halaqat" && method === "POST") {
      const body = request.postDataJSON();
      const created = { ...halaqa, ...body };
      halaqat = [created, ...halaqat];
      return respond(created, 201);
    }
    if (path.endsWith("/enrollments") && method === "GET") {
      return respond(enrollments);
    }
    if (path.endsWith("/enrollments") && method === "POST") {
      const body = request.postDataJSON();
      const created = {
        id: "enrollment-1",
        halaqa_id: "halaqa-1",
        student_id: body.student_id,
        student_name: student.full_name,
        halaqa_name: halaqa.name,
        status: "active",
        created_at: "2026-11-04T10:00:00Z",
      };
      enrollments = [...enrollments, created];
      return respond(created, 201);
    }
    return respond({ detail: `Unmocked: ${method} ${path}` }, 404);
  });

  return { getEnrollments: () => enrollments };
}

test("admin creates a teacher account", async ({ page }) => {
  await setup(page);
  await page.goto("/halaqat/admin");

  await page.getByLabel("اسم المعلم").fill("فاطمة أحمد");
  await page.getByLabel("البريد الإلكتروني").fill("fatma@example.test");
  await page.getByLabel("كلمة المرور المؤقتة")
    .fill("SecurePass12345!");

  await page.getByRole("button", { name: "إنشاء حساب المعلم" }).click();

  await expect(page.getByText(
    "تم إنشاء حساب المعلم واختياره للحلقة بنجاح",
  )).toBeVisible();

  await expect(page.locator("#halaqa-teacher"))
    .toHaveValue("teacher-2");
});

test("admin creates a halaqa", async ({ page }) => {
  await setup(page);
  await page.goto("/halaqat/admin");

  await page.locator("#halaqa-name").fill("حلقة الفاتحة");
  await page.locator("#halaqa-description").fill("حفظ ومراجعة");
  await page.locator("#halaqa-teacher").selectOption("teacher-1");

  await page.getByRole("button", { name: "إنشاء الحلقة" }).click();

  await expect(page.getByText("تم إنشاء الحلقة بنجاح")).toBeVisible();
  await expect(page.getByRole("region", {
    name: "الحلقات المنشأة في هذه الجلسة",
  })).toContainText("حلقة الفاتحة");
});

test("admin enrolls a student in a halaqa", async ({ page }) => {
  const mock = await setup(page);
  await page.goto("/halaqat/admin");

  await page.locator("#halaqa-name").fill("حلقة الفاتحة");
  await page.locator("#halaqa-teacher").selectOption("teacher-1");
  await page.getByRole("button", { name: "إنشاء الحلقة" }).click();
  await expect(page.getByText("تم إنشاء الحلقة بنجاح")).toBeVisible();

  await page.locator("#enrollment-halaqa").selectOption("halaqa-1");
  await page.locator("#enrollment-student").selectOption("student-1");
  await page.getByRole("button", { name: "تسجيل الطالب" }).click();

  await expect(page.getByText(
    "تم تسجيل الطالب في الحلقة بنجاح.",
  )).toBeVisible();
  await expect(page.getByText("عدد الطلاب المسجلين: 1")).toBeVisible();
  expect(mock.getEnrollments()).toHaveLength(1);
});

test("admin sees API error when teacher creation fails", async ({ page }) => {
  await setup(page);
  await page.route(`${api}/api/v1/admin/users`, async route => {
    if (route.request().method() !== "POST") {
      return route.fallback();
    }
    await route.fulfill({
      status: 409, headers: cors,
      json: { detail: "Teacher email already exists" },
    });
  });

  await page.goto("/halaqat/admin");
  await page.getByLabel("اسم المعلم").fill("فاطمة أحمد");
  await page.getByLabel("البريد الإلكتروني").fill("fatma@example.test");
  await page.getByLabel("كلمة المرور المؤقتة")
    .fill("SecurePass12345!");
  await page.getByRole("button", { name: "إنشاء حساب المعلم" }).click();

  await expect(page.getByRole("alert"))
    .toContainText("Teacher email already exists");
});

test("student cannot access admin halaqat", async ({ page }) => {
  await setup(page, "student");
  await page.goto("/halaqat/admin");

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByRole("heading", {
    name: "إنشاء حلقة قرآنية",
  })).toHaveCount(0);
});
