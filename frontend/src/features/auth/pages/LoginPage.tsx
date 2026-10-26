import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { BookOpen, LogIn } from "lucide-react";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
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
      await signIn({ email, password });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر تسجيل الدخول");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page" dir="rtl">
      <section className="auth-card">
        <div className="brand-icon"><BookOpen size={28} /></div>
        <p className="eyebrow">QURAN AI PLATFORM</p>
        <h1>مرحبًا بعودتك</h1>
        <p className="muted">سجّل دخولك لمتابعة رحلتك مع القرآن الكريم.</p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="email">البريد الإلكتروني</label>
          <input id="email" type="email" autoComplete="email"
            value={email} onChange={(e) => setEmail(e.target.value)}
            required />

          <label htmlFor="password">كلمة المرور</label>
          <input id="password" type="password" autoComplete="current-password"
            value={password} onChange={(e) => setPassword(e.target.value)}
            required />

          {error && <p className="form-error" role="alert">{error}</p>}

          <button type="submit" disabled={submitting}>
            <LogIn size={18} />
            {submitting ? "جاري تسجيل الدخول..." : "تسجيل الدخول"}
          </button>
        </form>

        <p className="auth-footer">
          ليس لديك حساب؟ <Link to="/register">إنشاء حساب جديد</Link>
        </p>
      </section>
    </main>
  );
}
