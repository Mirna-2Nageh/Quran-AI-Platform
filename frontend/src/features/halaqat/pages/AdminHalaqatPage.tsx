import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  createHalaqa,
  enrollStudent,
  getAllHalaqat,
  getEnrollments,
  type Halaqa,
  type Enrollment,
} from "../api/halaqat";
import { createTeacher, getAdminUsers, type DirectoryUser } from "../api/adminUsers";

export function AdminHalaqatPage() {
  const [teachers, setTeachers] = useState<DirectoryUser[]>([]);
  const [teacherName, setTeacherName] = useState("");
  const [teacherEmail, setTeacherEmail] = useState("");
  const [teacherPassword, setTeacherPassword] = useState("");
  const [creatingTeacher, setCreatingTeacher] = useState(false);
  const [teacherError, setTeacherError] = useState("");
  const [teacherMessage, setTeacherMessage] = useState("");

  const [allHalaqat, setAllHalaqat] = useState<Halaqa[]>([]);
  const [students, setStudents] = useState<DirectoryUser[]>([]);
  const [selectedHalaqa, setSelectedHalaqa] = useState("");
  const [selectedStudent, setSelectedStudent] = useState("");
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [enrollmentError, setEnrollmentError] = useState("");
  const [enrollmentMessage, setEnrollmentMessage] = useState("");
  const [enrolling, setEnrolling] = useState(false);
  const [loadingEnrollments, setLoadingEnrollments] = useState(false);
  const [enrollmentLoading, setEnrollmentLoading] = useState(true);

  const [created, setCreated] = useState<Halaqa[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    let active = true;

    getAdminUsers("teacher")
      .then((users) => {
        if (active) setTeachers(users);
      })
      .catch((err: unknown) => {
        if (active) {
          setError(err instanceof Error ? err.message : "تعذر تحميل المعلمين");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, []);


  useEffect(() => {
    let active = true;

    Promise.all([
      getAllHalaqat(),
      getAdminUsers("student"),
    ])
      .then(([halaqat, users]) => {
        if (!active) return;
        setAllHalaqat(halaqat);
        setStudents(users);
      })
      .catch((err: unknown) => {
        if (active) {
          setEnrollmentError(
            err instanceof Error ? err.message : "تعذر تحميل بيانات التسجيل",
          );
        }
      })
      .finally(() => {
        if (active) setEnrollmentLoading(false);
      });

    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedHalaqa) return;

    let active = true;
    queueMicrotask(() => {
      if (active) setLoadingEnrollments(true);
    });
    getEnrollments(selectedHalaqa)
      .then((items) => {
        if (active) setEnrollments(items);
      })
      .catch((err: unknown) => {
        if (active) {
          setEnrollmentError(
            err instanceof Error ? err.message : "تعذر تحميل تسجيلات الحلقة",
          );
        }
      })
      .finally(() => {
        if (active) setLoadingEnrollments(false);
      });

    return () => { active = false; };
  }, [selectedHalaqa]);

  async function handleEnrollment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedHalaqa || !selectedStudent || enrolling ||
        loadingEnrollments || enrollmentError) return;

    setEnrollmentError("");
    setEnrollmentMessage("");
    setEnrolling(true);

    try {
      await enrollStudent(selectedHalaqa, selectedStudent);
      setEnrollments(await getEnrollments(selectedHalaqa));
      setSelectedStudent("");
      setEnrollmentMessage("تم تسجيل الطالب في الحلقة بنجاح.");
    } catch (err) {
      setEnrollmentError(
        err instanceof Error ? err.message : "تعذر تسجيل الطالب",
      );
    } finally {
      setEnrolling(false);
    }
  }

  async function handleCreateTeacher(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (creatingTeacher) return;

    setTeacherError("");
    setTeacherMessage("");
    setCreatingTeacher(true);

    try {
      const teacher = await createTeacher({
        full_name: teacherName.trim(),
        email: teacherEmail.trim().toLowerCase(),
        password: teacherPassword,
      });

      setTeachers((previous) => [
        teacher,
        ...previous.filter((item) => item.id !== teacher.id),
      ]);
      setTeacherId(teacher.id);
      setTeacherName("");
      setTeacherEmail("");
      setTeacherPassword("");
      setTeacherMessage("تم إنشاء حساب المعلم واختياره للحلقة بنجاح");
    } catch (err) {
      setTeacherError(
        err instanceof Error ? err.message : "تعذر إنشاء حساب المعلم",
      );
    } finally {
      setCreatingTeacher(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !teacherId || submitting) return;

    setError("");
    setMessage("");
    setSubmitting(true);

    try {
      const halaqa = await createHalaqa({
        name: name.trim(),
        description: description.trim() || null,
        teacher_id: teacherId,
      });

      setCreated((previous) => [halaqa, ...previous]);
      setAllHalaqat((previous) => [
        halaqa,
        ...previous.filter((item) => item.id !== halaqa.id),
      ]);
      setName("");
      setDescription("");
      setTeacherId("");
      setMessage("تم إنشاء الحلقة بنجاح");
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر إنشاء الحلقة");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="dashboard" dir="rtl">
      <section className="dashboard-content">
        <Link to="/dashboard">العودة إلى لوحة التحكم</Link>
        <p className="eyebrow">إدارة الحلقات</p>
        <h1>إنشاء حلقة قرآنية</h1>
        <p className="muted">
          اختاري المعلم من القائمة، ثم أدخلي بيانات الحلقة.
        </p>


        <section aria-labelledby="create-teacher-title">
          <h2 id="create-teacher-title">إضافة معلم جديد</h2>
          <p className="muted">
            أنشئي حساب المعلم أولًا، ثم اختاريه لإدارة الحلقة.
          </p>

          {teacherError && (
            <p className="form-error" role="alert">{teacherError}</p>
          )}
          {teacherMessage && <p role="status">{teacherMessage}</p>}

          <form onSubmit={handleCreateTeacher}>
            <label htmlFor="teacher-full-name">اسم المعلم</label>
            <input
              id="teacher-full-name"
              value={teacherName}
              onChange={(event) => setTeacherName(event.target.value)}
              minLength={2}
              maxLength={100}
              autoComplete="off"
              required
            />

            <label htmlFor="teacher-email">البريد الإلكتروني</label>
            <input
              id="teacher-email"
              type="email"
              value={teacherEmail}
              onChange={(event) => setTeacherEmail(event.target.value)}
              autoComplete="off"
              required
            />

            <label htmlFor="teacher-password">كلمة المرور المؤقتة</label>
            <input
              id="teacher-password"
              type="password"
              value={teacherPassword}
              onChange={(event) => setTeacherPassword(event.target.value)}
              minLength={12}
              maxLength={128}
              autoComplete="new-password"
              required
            />

            <button
              className="primary-button"
              type="submit"
              disabled={creatingTeacher}
            >
              {creatingTeacher ? "جاري إنشاء الحساب..." : "إنشاء حساب المعلم"}
            </button>
          </form>
        </section>

        <hr />

        {error && <p className="form-error" role="alert">{error}</p>}
        {message && <p role="status">{message}</p>}

        <form onSubmit={handleSubmit}>
          <label htmlFor="halaqa-name">اسم الحلقة</label>
          <input
            id="halaqa-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={120}
            required
          />

          <label htmlFor="halaqa-description">الوصف</label>
          <textarea
            id="halaqa-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={3}
          />

          <label htmlFor="halaqa-teacher">المعلم</label>
          <select
            id="halaqa-teacher"
            value={teacherId}
            onChange={(event) => setTeacherId(event.target.value)}
            disabled={loading || submitting}
            required
          >
            <option value="">
              {loading ? "جاري تحميل المعلمين..." : "اختاري المعلم"}
            </option>
            {teachers.map((teacher) => (
              <option key={teacher.id} value={teacher.id}>
                {teacher.full_name} ({teacher.email})
              </option>
            ))}
          </select>

          {!loading && teachers.length === 0 && (
            <p className="muted">لا يوجد معلمون متاحون حاليًا.</p>
          )}

          <button
            className="primary-button"
            type="submit"
            disabled={loading || submitting || teachers.length === 0}
          >
            {submitting ? "جاري الإنشاء..." : "إنشاء الحلقة"}
          </button>
        </form>

        <hr />

        <section aria-labelledby="enrollment-title">
          <h2 id="enrollment-title">تسجيل الطلاب في الحلقات</h2>
          <p className="muted">
            اختاري الحلقة والطالب لإضافته إلى قائمة الطلاب المسجلين.
          </p>

          {enrollmentError && (
            <p className="form-error" role="alert">{enrollmentError}</p>
          )}
          {enrollmentMessage && (
            <p role="status">{enrollmentMessage}</p>
          )}

          <form onSubmit={(event) => { void handleEnrollment(event); }}>
            <label htmlFor="enrollment-halaqa">الحلقة</label>
            <select
              id="enrollment-halaqa"
              value={selectedHalaqa}
              onChange={(event) => {
                setSelectedHalaqa(event.target.value);
                setEnrollments([]);
                setSelectedStudent("");
                setEnrollmentMessage("");
                setEnrollmentError("");
              }}
              disabled={enrollmentLoading || enrolling}
              required
            >
              <option value="">اختاري الحلقة</option>
              {allHalaqat.map((halaqa) => (
                <option key={halaqa.id} value={halaqa.id}>
                  {halaqa.name}
                </option>
              ))}
            </select>

            <label htmlFor="enrollment-student">الطالب</label>
            <select
              id="enrollment-student"
              value={selectedStudent}
              onChange={(event) => setSelectedStudent(event.target.value)}
              disabled={!selectedHalaqa || enrollmentLoading || enrolling}
              required
            >
              <option value="">اختاري الطالب</option>
              {students
                .filter((student) =>
                  !enrollments.some(
                    (item) => item.student_id === student.id,
                  ),
                )
                .map((student) => (
                  <option key={student.id} value={student.id}>
                    {student.full_name} ({student.email})
                  </option>
                ))}
            </select>

            <button
              className="primary-button"
              type="submit"
              disabled={
                enrolling ||
                enrollmentLoading ||
                loadingEnrollments ||
                Boolean(enrollmentError) ||
                !selectedHalaqa ||
                !selectedStudent
              }
            >
              {enrolling ? "جاري التسجيل..." : "تسجيل الطالب"}
            </button>
          </form>

          {selectedHalaqa && (
            <p className="muted">
              عدد الطلاب المسجلين: {enrollments.length}
            </p>
          )}
        </section>

        {created.length > 0 && (
          <section aria-label="الحلقات المنشأة في هذه الجلسة">
            <h2>الحلقات المنشأة الآن</h2>
            <ul>
              {created.map((halaqa) => (
                <li key={halaqa.id}>{halaqa.name}</li>
              ))}
            </ul>
          </section>
        )}
      </section>
    </main>
  );
}
