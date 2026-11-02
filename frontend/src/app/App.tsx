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
import { MemorizationPage } from "../features/memorization/pages/MemorizationPage";

import { TeacherRoute } from "../features/halaqat/TeacherRoute";
import { TeacherHalaqatPage } from "../features/halaqat/pages/TeacherHalaqatPage";

import { HalaqaDetailsPage } from "../features/halaqat/pages/HalaqaDetailsPage";

import { StudentRoute } from "../features/halaqat/StudentRoute";
import { StudentHalaqatPage } from "../features/halaqat/pages/StudentHalaqatPage";

import { AdminRoute } from "../features/halaqat/AdminRoute";
import { AdminHalaqatPage } from "../features/halaqat/pages/AdminHalaqatPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/memorization" element={<MemorizationPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/recitation" element={<RecitationPracticePage />} />
            <Route path="/recitation/history" element={<RecitationHistoryPage />} />
            <Route path="/quran" element={<QuranReaderPage />} />
            <Route path="/quran/:number" element={<SurahDetailPage />} />
            <Route element={<AdminRoute />}>
              <Route
                path="/halaqat/admin"
                element={<AdminHalaqatPage />}
              />
            </Route>
            <Route element={<StudentRoute />}>
              <Route path="/halaqat/student" element={<StudentHalaqatPage />} />
            </Route>
            <Route element={<TeacherRoute />}>
              <Route
                path="/halaqat/teacher"
                element={<TeacherHalaqatPage />}
              />
              <Route path="/halaqat/teacher/:halaqaId" element={<HalaqaDetailsPage />} />
            </Route>
          </Route>

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
