import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  createHalaqaSession,
  getHalaqa,
  getEnrollments,
  getHalaqaSessions,
  type Halaqa,
  type Enrollment,
  type HalaqaSession,
} from "../api/halaqat";

import { SessionAttendance } from "../components/SessionAttendance";

export function HalaqaDetailsPage() {
  const { halaqaId } = useParams<{ halaqaId: string }>();
  const [halaqa, setHalaqa] = useState<Halaqa | null>(null);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [sessions, setSessions] = useState<HalaqaSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sessionError, setSessionError] = useState("");
  const [sessionSuccess, setSessionSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [scheduledAt, setScheduledAt] = useState("");
  const [duration, setDuration] = useState(60);
  const [notes, setNotes] = useState("");

  useEffect(() => {
    if (!halaqaId) return;

    let active = true;

    Promise.all([
      getHalaqa(halaqaId),
      getEnrollments(halaqaId),
      getHalaqaSessions(halaqaId),
    ])
      .then(([details, students, meetings]) => {
        if (!active) return;
        setHalaqa(details);
        setEnrollments(students);
        setSessions(meetings);
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : "تعذر تحميل الحلقة");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [halaqaId]);

  async function handleCreateSession(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!halaqaId || submitting) return;

    setSessionError("");
    setSessionSuccess("");

    const date = new Date(scheduledAt);
    if (!scheduledAt || !Number.isFinite(date.getTime()) ||
        date.getTime() <= Date.now()) {
      setSessionError("اختاري موعدًا صحيحًا في المستقبل.");
      return;
    }

    setSubmitting(true);
    try {
      await createHalaqaSession(halaqaId, {
        scheduled_at: date.toISOString(),
        duration_minutes: duration,
        notes: notes.trim() || null,
      });

      setSessions(await getHalaqaSessions(halaqaId));
      setScheduledAt("");
      setNotes("");
      setSessionSuccess("تم إنشاء الجلسة بنجاح.");
    } catch (err) {
      setSessionError(
        err instanceof Error ? err.message : "تعذر إنشاء الجلسة",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="dashboard" dir="rtl">
      <section className="dashboard-content">
        <Link to="/halaqat/teacher">العودة إلى حلقاتي</Link>

        {loading && <p role="status">جاري تحميل بيانات الحلقة...</p>}
        {error && <p className="form-error" role="alert">{error}</p>}

        {!loading && !error && halaqa && (
          <>
            <h1>{halaqa.name}</h1>
            <p className="muted">{halaqa.description || "بدون وصف"}</p>
            <p>حالة الحلقة: {halaqa.status}</p>

            <h2>الطلاب المسجلون ({enrollments.length})</h2>
            {enrollments.length === 0 ? (
              <p>لا يوجد طلاب مسجلون.</p>
            ) : (
              <div className="feature-grid">
                {enrollments.map((student) => (
                  <article className="feature-card" key={student.id}>
                    <h3>الطالب: {student.student_name || student.student_id}</h3>
                    <p>حالة التسجيل: {student.status}</p>
                  </article>
                ))}
              </div>
            )}

            {halaqa.status === "active" && (
              <section>
                <h2>إنشاء جلسة جديدة</h2>
                <form onSubmit={(event) => { void handleCreateSession(event); }}>
                  <label htmlFor="halaqa-scheduled-at">تاريخ ووقت الجلسة</label>
                  <input
                    id="halaqa-scheduled-at"
                    type="datetime-local"
                    required
                    value={scheduledAt}
                    onChange={(event) => setScheduledAt(event.target.value)}
                  />

                  <label htmlFor="halaqa-duration">مدة الجلسة بالدقائق</label>
                  <input
                    id="halaqa-duration"
                    type="number"
                    min={15}
                    max={240}
                    required
                    value={duration}
                    onChange={(event) => setDuration(Number(event.target.value))}
                  />

                  <label htmlFor="halaqa-notes">ملاحظات الجلسة</label>
                  <textarea
                    id="halaqa-notes"
                    maxLength={1000}
                    rows={3}
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                  />

                  {sessionError && (
                    <p role="alert" className="form-error">{sessionError}</p>
                  )}
                  {sessionSuccess && (
                    <p role="status">{sessionSuccess}</p>
                  )}

                  <button type="submit" disabled={submitting}>
                    {submitting ? "جاري إنشاء الجلسة..." : "إنشاء الجلسة"}
                  </button>
                </form>
              </section>
            )}

            <h2>الجلسات ({sessions.length})</h2>
            {sessions.length === 0 ? (
              <p>لا توجد جلسات مجدولة.</p>
            ) : (
              <div className="feature-grid">
                {sessions.map((session) => (
                  <article className="feature-card" key={session.id}>
                    <h3>
                      {new Date(session.scheduled_at).toLocaleString("ar-EG")}
                    </h3>
                    <p>المدة: {session.duration_minutes} دقيقة</p>
                    <p>الحالة: {session.status}</p>
                    <p>{session.notes || "بدون ملاحظات"}</p>
                    <SessionAttendance
                      session={session}
                      enrollments={enrollments}
                      halaqaActive={halaqa.status === "active"}
                    />
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
