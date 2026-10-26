import { createContext } from "react";
import type {
  LoginPayload,
  RegisterPayload,
  User,
} from "../api/auth";

export interface AuthContextValue {
  user: User | null;
  loading: boolean;
  signIn: (payload: LoginPayload) => Promise<void>;
  signUp: (payload: RegisterPayload) => Promise<void>;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
