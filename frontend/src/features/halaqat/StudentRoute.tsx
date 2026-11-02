import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/hooks/useAuth";

export function StudentRoute() {
  const { user, loading } = useAuth();

  if (loading) return <p role="status">جاري التحقق من الحساب...</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "student") {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
