import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "../features/auth/context/AuthProvider";
import { ProtectedRoute } from "../components/layout/ProtectedRoute";
import { LoginPage } from "../features/auth/pages/LoginPage";
import { RegisterPage } from "../features/auth/pages/RegisterPage";
import { DashboardPage } from "../pages/DashboardPage";
import { RecitationPracticePage } from "../features/recitation/pages/RecitationPracticePage";
import { RecitationHistoryPage } from "../features/recitation/pages/RecitationHistoryPage";
import { QuranReaderPage } from "../features/quran/pages/QuranReaderPage";
import { SurahDetailPage } from "../features/quran/pages/SurahDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/recitation" element={<RecitationPracticePage />} />
            <Route path="/recitation/history" element={<RecitationHistoryPage />} />
            <Route path="/quran" element={<QuranReaderPage />} />
            <Route path="/quran/:number" element={<SurahDetailPage />} />
          </Route>

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
