import { useEffect, useState, type ReactNode } from "react";

import {
  getCurrentUser,
  login,
  logout,
  register,
  type LoginPayload,
  type RegisterPayload,
  type User,
} from "../api/auth";

import { AuthContext } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  async function signIn(payload: LoginPayload) {
    const currentUser = await login(payload);
    setUser(currentUser);
  }

  async function signUp(payload: RegisterPayload) {
    await register(payload);
    await signIn({
      email: payload.email,
      password: payload.password,
    });
  }

  async function signOut() {
    await logout();
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{ user, loading, signIn, signUp, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}
