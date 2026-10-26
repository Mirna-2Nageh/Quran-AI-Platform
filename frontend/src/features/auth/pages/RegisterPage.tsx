import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { BookOpen, UserPlus } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

export function RegisterPage() {
  const { user, signUp } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await signUp({
        full_name: fullName,
        email,
        password,
      });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر إنشاء الحساب");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page" dir="rtl">
      <section className="auth-card">
        <div className="brand-icon"><BookOpen size={28} /></div>
        <p className="eyebrow">QURAN AI PLATFORM</p>
        <h1>ابدأ رحلتك مع القرآن</h1>
        <p className="muted">أنشئ حسابًا للبدء في استخدام المنصة.</p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="fullName">الاسم الكامل</label>
          <input id="fullName" autoComplete="name"
            minLength={2} maxLength={100}
            value={fullName} onChange={(e) => setFullName(e.target.value)}
            required />

          <label htmlFor="email">البريد الإلكتروني</label>
          <input id="email" type="email" autoComplete="email"
            value={email} onChange={(e) => setEmail(e.target.value)}
            required />

          <label htmlFor="password">كلمة المرور</label>
          <input id="password" type="password" autoComplete="new-password"
            minLength={12} maxLength={128}
            value={password} onChange={(e) => setPassword(e.target.value)}
            required />
          <small>استخدم كلمة مرور لا تقل عن 12 حرفًا.</small>

          {error && <p className="form-error" role="alert">{error}</p>}

          <button type="submit" disabled={submitting}>
            <UserPlus size={18} />
            {submitting ? "جاري إنشاء الحساب..." : "إنشاء حساب"}
          </button>
        </form>

        <p className="auth-footer">
          لديك حساب بالفعل؟ <Link to="/login">تسجيل الدخول</Link>
        </p>
      </section>
    </main>
  );
}
