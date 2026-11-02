import { apiRequest } from "../../../services/api";
import { getCsrfToken } from "../../auth/api/auth";

export type DirectoryRole = "teacher" | "student";

export interface DirectoryUser {
  id: string;
  full_name: string;
  email: string;
  role: DirectoryRole;
}

export function getAdminUsers(
  role: DirectoryRole,
  limit = 100,
  offset = 0,
): Promise<DirectoryUser[]> {
  const params = new URLSearchParams({
    role,
    limit: String(limit),
    offset: String(offset),
  });

  return apiRequest<DirectoryUser[]>(
    `/api/v1/admin/users?${params.toString()}`,
  );
}


export interface CreateTeacherPayload {
  full_name: string;
  email: string;
  password: string;
}

export async function createTeacher(
  payload: CreateTeacherPayload,
): Promise<DirectoryUser> {
  const csrf = await getCsrfToken();

  return apiRequest<DirectoryUser>("/api/v1/admin/users", {
    method: "POST",
    headers: { "X-CSRF-Token": csrf },
    body: JSON.stringify(payload),
  });
}
