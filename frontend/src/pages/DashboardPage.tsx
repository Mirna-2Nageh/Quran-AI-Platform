import { useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, History, LogOut, Mic, Sparkles } from "lucide-react";
import { useAuth } from "../features/auth/hooks/useAuth";

export function DashboardPage() {
  const { user, signOut } = useAuth();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleLogout() {
    setError("");
    setSubmitting(true);
    try {
      await signOut();
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر تسجيل الخروج");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="dashboard" dir="rtl">
      <header className="dashboard-header">
        <div className="brand">
          <BookOpen size={26} />
          <strong>Quran AI</strong>
        </div>
        <button className="secondary-button" onClick={handleLogout}
          disabled={submitting}>
          <LogOut size={17} />
          {submitting ? "جاري الخروج..." : "تسجيل الخروج"}
        </button>
      </header>

      <section className="dashboard-content">
        <p className="eyebrow">لوحة التحكم</p>
        <h1>السلام عليكم، {user?.full_name}</h1>
        <p className="muted">أهلًا بك في منصة القرآن الكريم.</p>
        {error && <p className="form-error" role="alert">{error}</p>}

        <div className="feature-grid">
          <Link to="/quran" className="feature-card feature-card-link">
            <BookOpen size={30} />
            <h2>قراءة القرآن</h2>
            <p>تصفح الآيات والسور بسهولة.</p>
            <span>ابدأ القراءة ←</span>
          </Link>

          <Link to="/recitation" className="feature-card feature-card-link">
            <Mic size={30} />
            <h2>تدريب التلاوة</h2>
            <p>قارن نص التلاوة بالنص القرآني المتوقع.</p>
            <span>تجربة المقارنة النصية ←</span>
          </Link>

          <Link
            to="/recitation/history"
            className="feature-card feature-card-link"
          >
            <History size={30} />
            <h2>سجل التلاوات</h2>
            <p>راجع محاولات التلاوة السابقة ونتائج مقارنة الكلمات.</p>
            <span>عرض سجل التلاوات ←</span>
          </Link>

          <article className="feature-card">
            <Sparkles size={30} />
            <h2>المساعد الذكي</h2>
            <p>مساعد للتعلم والاستفسارات المرتبطة بالقرآن.</p>
            <span>قريبًا</span>
          </article>
        </div>
      </section>
    </main>
  );
}
