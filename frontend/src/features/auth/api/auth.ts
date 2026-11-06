import { apiRequest } from "../../../services/api";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  full_name: string;
  password: string;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

let csrfToken: string | null = null;

export async function login(payload: LoginPayload): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail ?? "Login failed");
  }

  csrfToken = response.headers.get("X-CSRF-Token");

  return response.json() as Promise<User>;
}

export function register(payload: RegisterPayload): Promise<User> {
  return apiRequest<User>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getCurrentUser(): Promise<User> {
  return apiRequest<User>("/api/v1/auth/me");
}

let csrfRefreshPromise: Promise<void> | null = null;

export async function refreshCsrf(): Promise<void> {
  if (!csrfRefreshPromise) {
    csrfRefreshPromise = (async () => {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/csrf`, {
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Unable to refresh CSRF token");
      }

      const token = response.headers.get("X-CSRF-Token");
      if (!token) {
        throw new Error("CSRF token missing");
      }

      csrfToken = token;
    })().finally(() => {
      csrfRefreshPromise = null;
    });
  }

  return csrfRefreshPromise;
}

export async function logout(): Promise<void> {
  if (!csrfToken) {
    await refreshCsrf();
  }

  await apiRequest("/api/v1/auth/logout", {
    method: "POST",
    headers: {
      "X-CSRF-Token": csrfToken ?? "",
    },
  });

  csrfToken = null;
}

export async function getCsrfToken(): Promise<string> {
  if (!csrfToken) {
    await refreshCsrf();
  }

  if (!csrfToken) {
    throw new Error("CSRF token unavailable");
  }

  return csrfToken;
}
