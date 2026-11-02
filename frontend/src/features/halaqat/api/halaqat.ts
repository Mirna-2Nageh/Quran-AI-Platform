import { getCsrfToken } from "../../auth/api/auth";
import { apiRequest } from "../../../services/api";

const BASE = "/api/v1/halaqat";

export type HalaqaStatus = "active" | "paused" | "completed";
export type EnrollmentStatus = "active" | "withdrawn";
export type SessionStatus = "scheduled" | "completed" | "cancelled";
export type AttendanceStatus = "present" | "absent" | "late" | "excused";

export interface Halaqa {
  id: string;
  name: string;
  description: string | null;
  teacher_id: string;
  status: HalaqaStatus;
  created_at: string;
  updated_at: string;
}

export interface Enrollment {
  id: string;
  halaqa_id: string;
  student_id: string;
  student_name: string | null;
  halaqa_name: string | null;
  status: EnrollmentStatus;
  created_at: string;
}

export interface HalaqaSession {
  id: string;
  halaqa_id: string;
  scheduled_at: string;
  duration_minutes: number;
  notes: string | null;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
}

export interface AttendanceRecord {
  halaqa_name: string | null;
  session_scheduled_at: string | null;
  id: string;
  session_id: string;
  student_id: string;
  status: AttendanceStatus;
  notes: string | null;
  recorded_by: string;
  created_at: string;
  updated_at: string;
}

async function writeRequest<T>(
  path: string,
  method: "POST" | "PUT",
  payload: unknown,
): Promise<T> {
  const csrf = await getCsrfToken();

  return apiRequest<T>(path, {
    method,
    headers: { "X-CSRF-Token": csrf },
    body: JSON.stringify(payload),
  });
}

export const getAllHalaqat = (limit = 100, offset = 0) =>
  apiRequest<Halaqa[]>(
    `${BASE}?limit=${limit}&offset=${offset}`,
  );

export const getMyHalaqat = () =>
  apiRequest<Halaqa[]>(`${BASE}/my`);

export const getMyEnrollments = () =>
  apiRequest<Enrollment[]>(`${BASE}/my/enrollments`);

export const getHalaqa = (id: string) =>
  apiRequest<Halaqa>(`${BASE}/${encodeURIComponent(id)}`);

export const getEnrollments = (halaqaId: string) =>
  apiRequest<Enrollment[]>(
    `${BASE}/${encodeURIComponent(halaqaId)}/enrollments`,
  );

export const getHalaqaSessions = (halaqaId: string) =>
  apiRequest<HalaqaSession[]>(
    `${BASE}/${encodeURIComponent(halaqaId)}/sessions`,
  );

export const getSessionAttendance = (sessionId: string) =>
  apiRequest<AttendanceRecord[]>(
    `${BASE}/sessions/${encodeURIComponent(sessionId)}/attendance`,
  );

export const getMyAttendance = () =>
  apiRequest<AttendanceRecord[]>(`${BASE}/my/attendance`);

export const createHalaqa = (payload: {
  name: string;
  description?: string | null;
  teacher_id: string;
}) => writeRequest<Halaqa>(BASE, "POST", payload);

export const enrollStudent = (
  halaqaId: string,
  studentId: string,
) => writeRequest<Enrollment>(
  `${BASE}/${encodeURIComponent(halaqaId)}/enrollments`,
  "POST",
  { student_id: studentId },
);

export const createHalaqaSession = (
  halaqaId: string,
  payload: {
    scheduled_at: string;
    duration_minutes: number;
    notes?: string | null;
  },
) => writeRequest<HalaqaSession>(
  `${BASE}/${encodeURIComponent(halaqaId)}/sessions`,
  "POST",
  payload,
);

export const recordAttendance = (
  sessionId: string,
  payload: {
    student_id: string;
    status: AttendanceStatus;
    notes?: string | null;
  },
) => writeRequest<AttendanceRecord>(
  `${BASE}/sessions/${encodeURIComponent(sessionId)}/attendance`,
  "PUT",
  payload,
);
