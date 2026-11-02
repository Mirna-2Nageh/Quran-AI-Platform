import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getMyEnrollments,
  getMyAttendance,
  type Enrollment,
  type AttendanceRecord,
} from "../api/halaqat";

const enrollmentLabels: Record<string, string> = {
  active: "نشط",
  withdrawn: "منسحب",
};

const attendanceLabels: Record<string, string> = {
  present: "حاضر",
  absent: "غائب",
  late: "متأخر",
  excused: "بعذر",
};

function formatSessionDate(value: string | null): string {
  if (!value) return "غير متاح";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "غير متاح";

  return new Intl.DateTimeFormat("ar-EG", {
    timeZone: "Africa/Cairo",
    dateStyle: "long",
    timeStyle: "short",
  }).format(date);
}

export function StudentHalaqatPage() {
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    Promise.all([getMyEnrollments(), getMyAttendance()])
      .then(([studentEnrollments, studentAttendance]) => {
        if (!active) return;
        setEnrollments(studentEnrollments);
        setAttendance(studentAttendance);
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : "تعذر تحميل البيانات");
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
        <Link to="/dashboard">العودة إلى لوحة التحكم</Link>
        <h1>حلقاتي الدراسية</h1>
        <p className="muted">تابع حلقات القرآن الكريم وسجل حضورك.</p>

        {loading && <p role="status">جاري تحميل البيانات...</p>}
        {error && <p role="alert" className="form-error">{error}</p>}

        {!loading && !error && (
          <>
            <h2>الحلقات المسجل بها ({enrollments.length})</h2>
            {enrollments.length === 0 ? (
              <p>لم يتم تسجيلك في أي حلقة بعد.</p>
            ) : (
              <div className="feature-grid">
                {enrollments.map((item) => (
                  <article className="feature-card" key={item.id}>
                    <h3>الحلقة: {item.halaqa_name || 'غير متاحة'}</h3>
                    <p>حالة التسجيل: {enrollmentLabels[item.status] || item.status}</p>
                  </article>
                ))}
              </div>
            )}

            <h2>سجل الحضور ({attendance.length})</h2>
            {attendance.length === 0 ? (
              <p>لا يوجد سجل حضور حتى الآن.</p>
            ) : (
              <div className="feature-grid">
                {attendance.map((item) => (
                  <article className="feature-card" key={item.id}>
                    <h3>الحلقة: {item.halaqa_name || 'غير متاحة'}</h3>
                    <p>موعد الجلسة: {formatSessionDate(item.session_scheduled_at)}</p>
                    <p>حالة الحضور: {attendanceLabels[item.status] || item.status}</p>
                    {item.notes && <p>{item.notes}</p>}
                  </article>
                ))}
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}
