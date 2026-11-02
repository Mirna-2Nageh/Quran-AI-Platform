import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/hooks/useAuth";

export function TeacherRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return <p role="status">جاري تحميل الحساب...</p>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return user.role === "teacher"
    ? <Outlet />
    : <Navigate to="/dashboard" replace />;
}
