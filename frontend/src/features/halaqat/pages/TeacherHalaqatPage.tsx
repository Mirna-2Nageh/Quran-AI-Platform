import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, CalendarDays } from "lucide-react";

import { getMyHalaqat, type Halaqa } from "../api/halaqat";

export function TeacherHalaqatPage() {
  const [halaqat, setHalaqat] = useState<Halaqa[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    getMyHalaqat()
      .then((data) => {
        if (active) setHalaqat(data);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof Error ? err.message : "تعذر تحميل الحلقات",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="dashboard" dir="rtl">
      <section className="dashboard-content">
        <Link to="/dashboard">العودة للوحة التحكم</Link>

        <p className="eyebrow">إدارة الحلقات</p>
        <h1>حلقاتي التعليمية</h1>
        <p className="muted">
          متابعة حلقات القرآن الكريم والجلسات التعليمية.
        </p>

        {loading && <p role="status">جاري تحميل الحلقات...</p>}

        {error && <p className="form-error" role="alert">{error}</p>}

        {!loading && !error && halaqat.length === 0 && (
          <p>لا توجد حلقات مسندة إليك حاليًا.</p>
        )}

        {!loading && !error && halaqat.length > 0 && (
          <div className="feature-grid">
            {halaqat.map((halaqa) => (
              <Link to={`/halaqat/teacher/${halaqa.id}`} className="feature-card feature-card-link" key={halaqa.id}>
                <BookOpen size={30} />
                <h2>{halaqa.name}</h2>
                <p>{halaqa.description || "حلقة تعليم القرآن الكريم"}</p>
                <p>
                  الحالة:{" "}
                  {halaqa.status === "active"
                    ? "نشطة"
                    : halaqa.status === "paused"
                      ? "متوقفة مؤقتًا"
                      : "مكتملة"}
                </p>
                <CalendarDays size={20} />
                <span>تفاصيل الجلسات قريبًا</span>
              </Link>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
