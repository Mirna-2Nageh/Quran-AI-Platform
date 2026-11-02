import { useEffect, useState } from "react";
import {
  getSessionAttendance,
  recordAttendance,
  type AttendanceRecord,
  type AttendanceStatus,
  type Enrollment,
  type HalaqaSession,
} from "../api/halaqat";

const statusLabels: Record<AttendanceStatus, string> = {
  present: "حاضر",
  absent: "غائب",
  late: "متأخر",
  excused: "بعذر",
};

interface Props {
  session: HalaqaSession;
  enrollments: Enrollment[];
  halaqaActive: boolean;
}

export function SessionAttendance({
  session,
  enrollments,
  halaqaActive,
}: Props) {
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [error, setError] = useState("");
  const [busyStudent, setBusyStudent] = useState<string | null>(null);

  const [currentTime, setCurrentTime] = useState<number | null>(null);

  useEffect(() => {
    const updateTime = () => setCurrentTime(Date.now());

    updateTime();
    const interval = setInterval(updateTime, 30_000);

    return () => clearInterval(interval);
  }, []);

  const canRecord =
    halaqaActive &&
    session.status !== "cancelled" &&
    currentTime !== null &&
    new Date(session.scheduled_at).getTime() <= currentTime;

  const activeStudents = enrollments.filter(
    (item) => item.status === "active",
  );

  useEffect(() => {
    let active = true;

    getSessionAttendance(session.id)
      .then((data) => {
        if (active) setRecords(data);
      })
      .catch((err) => {
        if (active) {
          setLoadFailed(true);
          setError(
            err instanceof Error ? err.message : "تعذر تحميل الحضور",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [session.id]);

  async function saveAttendance(
    studentId: string,
    status: AttendanceStatus,
  ) {
    if (!canRecord || loading || loadFailed || busyStudent) return;

    setBusyStudent(studentId);
    setError("");

    try {
      const saved = await recordAttendance(session.id, {
        student_id: studentId,
        status,
        notes: null,
      });

      setRecords((current) => [
        ...current.filter((item) => item.student_id !== studentId),
        saved,
      ]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "تعذر تسجيل الحضور",
      );
    } finally {
      setBusyStudent(null);
    }
  }

  return (
    <section>
      <h4>سجل الحضور</h4>

      {loading && <p role="status">جاري تحميل الحضور...</p>}
      {error && <p className="form-error" role="alert">{error}</p>}

      {!canRecord && (
        <p className="muted">
          تسجيل الحضور غير متاح قبل بدء الجلسة أو عند إيقاف الحلقة أو إلغاء الجلسة.
        </p>
      )}

      {!loading && activeStudents.length === 0 && (
        <p>لا يوجد طلاب نشطون في الحلقة.</p>
      )}

      {!loading && activeStudents.map((student) => {
        const current = records.find(
          (item) => item.student_id === student.student_id,
        );

        return (
          <div key={student.id}>
            <p>الطالب: {student.student_name || student.student_id}</p>

            <label>
              حالة الحضور
              <select
                aria-label={`حضور الطالب ${student.student_name || student.student_id}`}
                value={current?.status ?? ""}
                disabled={!canRecord || loading || loadFailed || busyStudent !== null}
                onChange={(event) => {
                  void saveAttendance(
                    student.student_id,
                    event.target.value as AttendanceStatus,
                  );
                }}
              >
                <option value="" disabled>اختاري الحالة</option>
                {Object.entries(statusLabels).map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
          </div>
        );
      })}
    </section>
  );
}
