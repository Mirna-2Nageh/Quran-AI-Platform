import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createPlan,
  createSession,
  getProgress,
  listPlans,
  listSessions,
  updatePlan,
  type MemorizationPlan,
  type MemorizationProgress,
  type MemorizationSession,
  type PlanStatus,
  type SessionResult,
  type SessionType,
} from "../api/memorization";

const sessionTypeLabels: Record<SessionType, string> = {
  memorization: "حفظ",
  revision: "مراجعة",
};

const sessionResultLabels: Record<SessionResult, string> = {
  completed: "مكتملة",
  needs_review: "تحتاج مراجعة",
  incomplete: "غير مكتملة",
};

export function MemorizationPage() {
  const [plans, setPlans] = useState<MemorizationPlan[]>([]);
  const [progress, setProgress] = useState<MemorizationProgress | null>(null);
  const [sessions, setSessions] = useState<MemorizationSession[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [surah, setSurah] = useState(1);
  const [start, setStart] = useState(1);
  const [end, setEnd] = useState(7);
  const [sessionType, setSessionType] = useState<SessionType>("memorization");
  const [sessionResult, setSessionResult] = useState<SessionResult>("completed");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editingId, setEditingId] = useState("");
  const [editSurah, setEditSurah] = useState(1);
  const [editStart, setEditStart] = useState(1);
  const [editEnd, setEditEnd] = useState(1);

  const refresh = useCallback(async () => {
    const [nextPlans, nextProgress] = await Promise.all([
      listPlans(),
      getProgress(),
    ]);
    setPlans(nextPlans);
    setProgress(nextProgress);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([listPlans(), getProgress()])
      .then(([nextPlans, nextProgress]) => {
        if (active) {
          setPlans(nextPlans);
          setProgress(nextProgress);
        }
      })
      .catch((err: unknown) => {
        if (active) setError(String(err));
      });
    return () => { active = false; };
  }, []);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await action();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر تنفيذ الطلب");
    } finally {
      setBusy(false);
    }
  }

  async function openSessions(id: string) {
    setSelectedId(id);
    setSessions([]);
    setError("");
    try {
      setSessions(await listSessions(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر تحميل الجلسات");
    }
  }

  return (
    <main className="memorization-page" dir="rtl">
      <nav className="memorization-nav"><Link to="/dashboard">لوحة التحكم</Link> / الحفظ والمراجعة</nav>
      <h1>الحفظ والمراجعة</h1>
      <p className="muted">نظّم خطط الحفظ، وسجّل جلسات المراجعة، وتابع تقدّمك.</p>

      {error && <p role="alert" style={{ color: "crimson" }}>{error}</p>}

      <section>
        <h2>تقدّم الحفظ</h2>
        {progress ? (
          <>
            <p>نسبة الإنجاز: {progress.completion_rate}%</p>
            <progress value={progress.completion_rate} max={100} />
            <p>الخطط المكتملة: {progress.completed_plans}/{progress.total_plans}</p>
            <p>الآيات المكتملة: {progress.completed_ayahs}/{progress.unique_planned_ayahs}</p>
            <p>جلسات المراجعة: {progress.revision_sessions}</p>
          </>
        ) : <p>جاري تحميل التقدم...</p>}
      </section>

      <section>
        <h2>إنشاء خطة حفظ</h2>
        <form onSubmit={(event) => {
          event.preventDefault();
          void run(() => createPlan({
            surah_number: surah,
            start_ayah: start,
            end_ayah: end,
          }));
        }}>
          <label>رقم السورة
            <input type="number" min={1} max={114} required value={surah}
              onChange={(e) => setSurah(Number(e.target.value))} />
          </label>
          <label>من الآية
            <input type="number" min={1} required value={start}
              onChange={(e) => setStart(Number(e.target.value))} />
          </label>
          <label>إلى الآية
            <input type="number" min={start} required value={end}
              onChange={(e) => setEnd(Number(e.target.value))} />
          </label>
          <button disabled={busy} type="submit">إنشاء الخطة</button>
        </form>
      </section>

      <section>
        <h2>خطط الحفظ</h2>
        {plans.length === 0 && <p>لا توجد خطط حفظ بعد.</p>}
        {plans.map((plan) => (
          <article key={plan.id} style={{
            border: "1px solid #ccc", padding: 16, marginBottom: 12,
            borderRadius: 8,
          }}>
            <h3>السورة {plan.surah_number} — الآيات {plan.start_ayah}–{plan.end_ayah}</h3>
            <label>الحالة
              <select value={plan.status} disabled={busy || plan.status === "archived"}
                onChange={(e) => {
                  const nextStatus = e.target.value as PlanStatus;
                  if (
                    nextStatus === "archived" &&
                    !window.confirm("هل تريد أرشفة هذه الخطة؟ ستبقى جلساتها السابقة محفوظة.")
                  ) {
                    e.target.value = plan.status;
                    return;
                  }
                  void run(() => updatePlan(plan.id, nextStatus));
                }}>
                <option value="active">نشطة</option>
                <option value="completed">مكتملة</option>
                <option value="paused">متوقفة مؤقتًا</option>
                <option value="archived">مؤرشفة</option>
              </select>
            </label>
            {plan.status !== "archived" && (
              <button type="button" disabled={busy} onClick={() => {
                setEditingId(plan.id);
                setEditSurah(plan.surah_number);
                setEditStart(plan.start_ayah);
                setEditEnd(plan.end_ayah);
              }}>
                تعديل الخطة
              </button>
            )}
            {editingId === plan.id && (
              <form onSubmit={(event) => {
                event.preventDefault();
                void run(async () => {
                  await updatePlan(plan.id, {
                    surah_number: editSurah,
                    start_ayah: editStart,
                    end_ayah: editEnd,
                  });
                  setEditingId("");
                });
              }}>
                <label>رقم السورة
                  <input type="number" min={1} max={114} required
                    value={editSurah}
                    onChange={(e) => setEditSurah(Number(e.target.value))} />
                </label>
                <label>من الآية
                  <input type="number" min={1} required value={editStart}
                    onChange={(e) => setEditStart(Number(e.target.value))} />
                </label>
                <label>إلى الآية
                  <input type="number" min={editStart} required value={editEnd}
                    onChange={(e) => setEditEnd(Number(e.target.value))} />
                </label>
                <button disabled={busy} type="submit">حفظ التعديلات</button>
                <button type="button" disabled={busy}
                  onClick={() => setEditingId("")}>إلغاء</button>
              </form>
            )}
            <button type="button" onClick={() => void openSessions(plan.id)}>
              عرض الجلسات
            </button>
          </article>
        ))}
      </section>

      {selectedId && (
        <section>
          <h2>جلسات الحفظ والمراجعة</h2>
          {sessions.length === 0 && <p>لا توجد جلسات مسجلة بعد.</p>}
          {sessions.map((session) => (
            <p key={session.id}>
              {sessionTypeLabels[session.session_type]} — {sessionResultLabels[session.result]} —{" "}
              {new Date(session.completed_at).toLocaleDateString("ar-EG")}
              {session.notes && ` — ${session.notes}`}
            </p>
          ))}

          {plans.find((plan) => plan.id === selectedId)?.status === "archived" ? (
            <p>هذه الخطة مؤرشفة. يمكنك مراجعة جلساتها السابقة فقط.</p>
          ) : (
          <form onSubmit={(event) => {
            event.preventDefault();
            void run(async () => {
              const planId = selectedId;
              await createSession(planId, {
                session_type: sessionType,
                result: sessionResult,
                notes: notes.trim() || null,
              });
              setNotes("");
              setSessions(await listSessions(planId));
            });
          }}>
            <label>نوع الجلسة
              <select value={sessionType}
                onChange={(e) => setSessionType(e.target.value as SessionType)}>
                <option value="memorization">حفظ</option>
                <option value="revision">مراجعة</option>
              </select>
            </label>
            <label>النتيجة
              <select value={sessionResult}
                onChange={(e) => setSessionResult(e.target.value as SessionResult)}>
                <option value="completed">مكتملة</option>
                <option value="needs_review">تحتاج مراجعة</option>
                <option value="incomplete">غير مكتملة</option>
              </select>
            </label>
            <label>ملاحظات
              <textarea maxLength={1000} value={notes}
                onChange={(e) => setNotes(e.target.value)} />
            </label>
            <button disabled={busy} type="submit">حفظ الجلسة</button>
          </form>
          )}
        </section>
      )}
    </main>
  );
}
