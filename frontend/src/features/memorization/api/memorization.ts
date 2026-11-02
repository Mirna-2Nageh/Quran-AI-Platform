import { getCsrfToken } from "../../auth/api/auth";
import { apiRequest } from "../../../services/api";

export type PlanStatus = "active" | "completed" | "paused";
export type SessionType = "memorization" | "revision";
export type SessionResult = "completed" | "needs_review" | "incomplete";

export interface MemorizationPlan {
  id: string;
  surah_number: number;
  start_ayah: number;
  end_ayah: number;
  status: PlanStatus;
  created_at: string;
  updated_at: string;
}

export interface MemorizationSession {
  id: string;
  plan_id: string;
  session_type: SessionType;
  result: SessionResult;
  notes: string | null;
  completed_at: string;
}

export interface MemorizationProgress {
  total_plans: number;
  completed_plans: number;
  unique_planned_ayahs: number;
  completed_ayahs: number;
  completion_rate: number;
  revision_sessions: number;
}

const BASE = "/api/v1/memorization";

async function writeRequest<T>(
  path: string,
  method: "POST" | "PATCH",
  payload: unknown,
): Promise<T> {
  const csrf = await getCsrfToken();
  return apiRequest<T>(path, {
    method,
    headers: { "X-CSRF-Token": csrf },
    body: JSON.stringify(payload),
  });
}

export const listPlans = () =>
  apiRequest<MemorizationPlan[]>(`${BASE}/plans`);

export const getProgress = () =>
  apiRequest<MemorizationProgress>(`${BASE}/progress`);

export const createPlan = (payload: {
  surah_number: number;
  start_ayah: number;
  end_ayah: number;
}) => writeRequest<MemorizationPlan>(`${BASE}/plans`, "POST", payload);

export const updatePlan = (id: string, status: PlanStatus) =>
  writeRequest<MemorizationPlan>(
    `${BASE}/plans/${encodeURIComponent(id)}`,
    "PATCH",
    { status },
  );

export const listSessions = (id: string) =>
  apiRequest<MemorizationSession[]>(
    `${BASE}/plans/${encodeURIComponent(id)}/sessions`,
  );

export const createSession = (
  id: string,
  payload: {
    session_type: SessionType;
    result: SessionResult;
    notes: string | null;
  },
) =>
  writeRequest<MemorizationSession>(
    `${BASE}/plans/${encodeURIComponent(id)}/sessions`,
    "POST",
    payload,
  );
