import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/hooks/useAuth";

export function AdminRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return <p role="status">جاري تحميل الحساب...</p>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return user.role === "admin"
    ? <Outlet />
    : <Navigate to="/dashboard" replace />;
}
