import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../features/auth/hooks/useAuth";

export function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>جاري تحميل الحساب...</div>;
  }

  return user ? <Outlet /> : <Navigate to="/login" replace />;
}
