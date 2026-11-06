import { AudioRecorder } from "../components/AudioRecorder";
import { LiveMemorizationRecorder } from "../components/LiveMemorizationRecorder";
import { buildWordFeedback, tokenizeExpectedWords } from "../utils/wordFeedback";
import type { AudioAnalysisResponse, LiveCorrectionResponse } from "../api/audio";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { BookOpen, GitCompareArrows } from "lucide-react";

import { getSurah, type SurahDetail } from "../../quran/api/quran";
import {
  createSession,
  listPlans,
  type MemorizationPlan,
  type SessionType,
  type SessionResult,
} from "../../memorization/api/memorization";
import {
  alignRecitation,
  type AlignmentResponse,
  type AlignmentIssue,
} from "../api/recitation";

const issueLabels: Record<AlignmentIssue["operation"], string> = {
  substitution: "كلمة مختلفة",
  deletion: "كلمة ناقصة",
  insertion: "كلمة إضافية",
};

export function RecitationPracticePage() {
  const [searchParams] = useSearchParams();

  const requestedSurah = Number(searchParams.get("surah"));
  const requestedAyah = Number(searchParams.get("ayah"));

  const initialSurah =
    Number.isInteger(requestedSurah) &&
    requestedSurah >= 1 &&
    requestedSurah <= 114
      ? requestedSurah
      : 1;

  const initialAyah =
    Number.isInteger(requestedAyah) && requestedAyah >= 1
      ? requestedAyah
      : 1;

  const [surahNumber, setSurahNumber] = useState(initialSurah);
  const [requestedSelection, setRequestedSelection] = useState({
    surah: initialSurah,
    ayah: initialAyah,
  });
  const [surah, setSurah] = useState<SurahDetail | null>(null);
  const [ayahNumber, setAyahNumber] = useState(1);
  const [endAyahNumber, setEndAyahNumber] = useState(1);
  const [recognizedText, setRecognizedText] = useState("");
  const [liveFeedback, setLiveFeedback] = useState<LiveCorrectionResponse | null>(null);
  const [result, setResult] = useState<AlignmentResponse | null>(null);
  const [recitationSessionId, setRecitationSessionId] = useState<string | null>(null);
  const [memorizationPlans, setMemorizationPlans] = useState<MemorizationPlan[]>([]);
  const [plansError, setPlansError] = useState("");
  const [selectedPlanId, setSelectedPlanId] = useState("");
  const [sessionType, setSessionType] = useState<SessionType>("memorization");
  const [sessionResult, setSessionResult] = useState<SessionResult>("needs_review");
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState("");
  const [linkSuccess, setLinkSuccess] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const alignmentRequestId = useRef(0);

  useEffect(() => {
    let cancelled = false;

    getSurah(surahNumber)
      .then((data) => {
        if (!cancelled) {
          setSurah(data);
          const initialAyah =
            data.number === requestedSelection.surah &&
            requestedSelection.ayah <= data.numberOfAyahs
              ? requestedSelection.ayah
              : 1;

          setAyahNumber(initialAyah);
          setEndAyahNumber(initialAyah);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setSurah(null);
          setError(
            err instanceof Error ? err.message : "تعذر تحميل السورة",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [surahNumber, requestedSelection]);

  const selectedAyahs = surah?.ayahs.filter(
    (ayah) =>
      ayah.numberInSurah >= ayahNumber &&
      ayah.numberInSurah <= endAyahNumber,
  ) ?? [];

  const expectedText = selectedAyahs
    .map((ayah) => ayah.text)
    .join(" ");

  const hasSelection = selectedAyahs.length > 0;

  const wordFeedback =
    result && hasSelection
      ? buildWordFeedback(expectedText, result)
      : null;


  function invalidateAlignment() {
    setLiveFeedback(null);
    alignmentRequestId.current += 1;
    setRecitationSessionId(null);
    setMemorizationPlans([]);
    setPlansError("");
    setSelectedPlanId("");
    setLinkError("");
    setLinkSuccess(false);
    setLinking(false);
    setResult(null);
    setError("");
    setSubmitting(false);
  }

  function handleAudioAnalysis(
    analysis: AudioAnalysisResponse,
  ) {
    alignmentRequestId.current += 1;
    setRecognizedText(analysis.recognized_text);
    setRecitationSessionId(analysis.session_id);
    setSelectedPlanId("");
    setLinkError("");
    setLinkSuccess(false);
    setLinking(false);
    setMemorizationPlans([]);
    setPlansError("");
    const requestId = alignmentRequestId.current;
    void listPlans()
      .then((plans) => {
        if (requestId === alignmentRequestId.current) {
          setMemorizationPlans(plans);
        }
      })
      .catch((err: unknown) => {
        if (requestId === alignmentRequestId.current) {
          setPlansError(
            err instanceof Error ? err.message : "تعذر تحميل خطط الحفظ",
          );
        }
      });
    setResult(analysis.alignment);
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!hasSelection || !recognizedText.trim()) return;

    const requestId = ++alignmentRequestId.current;
    setError("");
    setSubmitting(true);
    setRecitationSessionId(null);
    setMemorizationPlans([]);
    setPlansError("");
    setSelectedPlanId("");
    setLinkError("");
    setLinkSuccess(false);
    setLinking(false);
    setResult(null);

    try {
      const response = await alignRecitation({
        expected_text: expectedText,
        recognized_text: recognizedText,
      });
      if (requestId === alignmentRequestId.current) {
        setResult(response);
      }
    } catch (err) {
      if (requestId === alignmentRequestId.current) {
        setError(
          err instanceof Error ? err.message : "تعذر مقارنة النصوص",
        );
      }
    } finally {
      if (requestId === alignmentRequestId.current) {
        setSubmitting(false);
      }
    }
  }

  async function handleLinkSession(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!recitationSessionId || !selectedPlanId || linking || linkSuccess) return;

    const requestId = alignmentRequestId.current;
    const sessionId = recitationSessionId;
    setLinking(true);
    setLinkError("");

    try {
      await createSession(selectedPlanId, {
        session_type: sessionType,
        result: sessionResult,
        notes: null,
        recitation_session_id: sessionId,
      });

      if (requestId === alignmentRequestId.current) {
        setLinkSuccess(true);
      }
    } catch (err: unknown) {
      if (requestId === alignmentRequestId.current) {
        setLinkError(
          err instanceof Error ? err.message : "تعذر ربط التلاوة بالخطة",
        );
      }
    } finally {
      if (requestId === alignmentRequestId.current) {
        setLinking(false);
      }
    }
  }

  function changeSurah(value: number) {
    invalidateAlignment();
    setRequestedSelection({ surah: value, ayah: 1 });
    setLoading(true);
    setError("");
    setResult(null);
    setRecognizedText("");
    setSurah(null);
    setSurahNumber(value);
  }

  function changeAyah(value: number) {
    invalidateAlignment();
    setAyahNumber(value);
    setEndAyahNumber((current) =>
      Math.min(Math.max(current, value), value + 9),
    );
    setRecognizedText("");
    setResult(null);
    setError("");
  }

  function changeEndAyah(value: number) {
    invalidateAlignment();
    setEndAyahNumber(value);
    setRecognizedText("");
    setResult(null);
    setError("");
  }

  return (
    <main className="quran-page" dir="rtl">
      <header className="quran-header">
        <Link to="/dashboard">العودة للوحة التحكم</Link>
        <div className="brand">
          <BookOpen size={25} />
          <strong>Quran AI</strong>
        </div>
      </header>

      <section className="quran-content recitation-content">
        <p className="eyebrow">RECITATION PRACTICE</p>
        <h1>مقارنة نص التلاوة</h1>
        <p className="muted">
          قارن النص المتوقع بنص تفريغ التلاوة. هذه الميزة
          تستخدم التعرف الآلي على الكلام لمقارنة الكلمات، ولا تقيّم أحكام التجويد أو مخارج الحروف بدقة.
        </p>

        <div className="recitation-panel">
          <div className="recitation-controls">
            <label>
              رقم السورة
              <select
                value={surahNumber}
                onChange={(event) =>
                  changeSurah(Number(event.target.value))
                }
              >
                {Array.from({ length: 114 }, (_, index) => (
                  <option key={index + 1} value={index + 1}>
                    {index + 1}
                  </option>
                ))}
              </select>
            </label>

            <label>
              من آية
              <select
                value={ayahNumber}
                disabled={!surah || loading}
                onChange={(event) =>
                  changeAyah(Number(event.target.value))
                }
              >
                {surah?.ayahs.map((ayah) => (
                  <option
                    key={ayah.numberInSurah}
                    value={ayah.numberInSurah}
                  >
                    {ayah.numberInSurah}
                  </option>
                ))}
              </select>
            </label>

            <label>
              إلى آية
              <select
                value={endAyahNumber}
                disabled={!surah || loading}
                onChange={(event) =>
                  changeEndAyah(Number(event.target.value))
                }
              >
                {surah?.ayahs
                  .filter(
                    (ayah) =>
                      ayah.numberInSurah >= ayahNumber &&
                      ayah.numberInSurah <= ayahNumber + 9,
                  )
                  .map((ayah) => (
                    <option
                      key={ayah.numberInSurah}
                      value={ayah.numberInSurah}
                    >
                      {ayah.numberInSurah}
                    </option>
                  ))}
              </select>
            </label>
          </div>

          {loading && <p role="status">جاري تحميل الآيات...</p>}

          {hasSelection && (
            <div className="expected-ayah" lang="ar">
              {selectedAyahs.map((ayah, ayahIndex) => {
                const precedingText = selectedAyahs
                  .slice(0, ayahIndex)
                  .map((item) => item.text)
                  .join(" ");

                const wordOffset = tokenizeExpectedWords(
                  precedingText,
                ).length;

                return (
                  <span key={ayah.number}>
                    {ayah.text.split(/(\\s+)/).map((part, partIndex) => {
                      if (!part.trim()) {
                        return <span key={partIndex}>{part}</span>;
                      }

                      const precedingParts = ayah.text
                        .split(/(\s+)/)
                        .slice(0, partIndex)
                        .join("");

                      const localIndex = tokenizeExpectedWords(
                        precedingParts,
                      ).length;

                      const isAlignableWord =
                        tokenizeExpectedWords(part).length === 1;

                      const feedback =
                        wordFeedback?.canHighlight && isAlignableWord
                          ? wordFeedback.words[wordOffset + localIndex]
                          : null;

                      return (
                        <span
                          key={partIndex}
                          className={
                            feedback
                              ? `recitation-feedback-word ${feedback.status}`
                              : undefined
                          }
                          title={
                            feedback?.status === "substituted"
                              ? `تم التعرف على: ${feedback.recognizedWord ?? "غير معروف"}`
                              : feedback?.status === "missing"
                                ? "الكلمة غير موجودة في النص المتعرف عليه"
                                : undefined
                          }
                        >
                          {part}
                        </span>
                      );
                    })}
                    {" "}﴿{ayah.numberInSurah}﴾{" "}
                  </span>
                );
              })}
            </div>
          )}

          {wordFeedback && (
            <div className="recitation-feedback-summary">
              <p>
                نسبة التطابق النصي:{" "}
                <strong>{wordFeedback.matchPercentage}%</strong>
              </p>

              {wordFeedback.canHighlight ? (
                <div
                  className="recitation-feedback-legend"
                  aria-label="دليل ألوان مقارنة الكلمات"
                >
                  <span className="recitation-feedback-word matched">
                    متطابقة نصيًا
                  </span>
                  <span className="recitation-feedback-word substituted">
                    مختلفة
                  </span>
                  <span className="recitation-feedback-word missing">
                    ناقصة
                  </span>
                </div>
              ) : (
                <p role="status">
                  تعذر ربط بعض الكلمات بالنص المعروض بدقة؛
                  لذلك تم تعطيل التلوين لتجنب نتائج مضللة.
                </p>
              )}

              {wordFeedback.extraWords.length > 0 && (
                <div className="recitation-extra-words">
                  <strong>كلمات إضافية في النص المتعرف عليه:</strong>
                  <p>
                    {wordFeedback.extraWords
                      .map((item) => item.word)
                      .join("، ")}
                  </p>
                </div>
              )}

              <small>
                هذه مقارنة نصية بعد التطبيع، وليست تقييمًا للتجويد
                أو مخارج الحروف.
              </small>
            </div>
          )}

          {hasSelection && ayahNumber === endAyahNumber && (
            <section className="recitation-live-section" aria-label="التسميع المباشر">
              <LiveMemorizationRecorder
                key={`${surahNumber}-${ayahNumber}`}
                surahNumber={surahNumber}
                ayahNumber={ayahNumber}
                onFeedback={setLiveFeedback}
                onFinalized={(sessionId) => {
                  alignmentRequestId.current += 1;
                  const requestId = alignmentRequestId.current;
                  setRecitationSessionId(sessionId);
                  setSelectedPlanId("");
                  setLinkError("");
                  setLinkSuccess(false);
                  setMemorizationPlans([]);
                  setPlansError("");
                  void listPlans()
                    .then((plans) => {
                      if (requestId === alignmentRequestId.current) {
                        setMemorizationPlans(plans);
                      }
                    })
                    .catch((err: unknown) => {
                      if (requestId === alignmentRequestId.current) {
                        setPlansError(
                          err instanceof Error ? err.message : "تعذر تحميل خطط الحفظ",
                        );
                      }
                    });
                }}
              />

              {liveFeedback && (
                <div className="recitation-live-feedback" dir="rtl">
                  <h3>نتيجة التسميع المباشر</h3>
                  <p>النص المتعرف عليه: {liveFeedback.recognized_text || "لم يتم التعرف على كلمات"}</p>
                  <div className="recitation-live-words" lang="ar">
                    {liveFeedback.word_feedback.map((item) => (
                      <span
                        key={item.index}
                        className={`recitation-feedback-word ${
                          item.status === "review" ? "substituted" : item.status
                        }`}
                        title={
                          item.status === "review"
                            ? `تحتاج مراجعة: ${item.recognized_word ?? "غير معروف"}`
                            : undefined
                        }
                      >
                        {item.word}{" "}
                      </span>
                    ))}
                  </div>
                  <p className="muted">
                    النتائج مبدئية وتعتمد على التعرف الآلي على الكلام،
                    وليست تقييمًا للتجويد أو مخارج الحروف.
                  </p>
                </div>
              )}
            </section>
          )}

          {hasSelection && (
            <AudioRecorder
              key={`${surahNumber}-${ayahNumber}-${endAyahNumber}`}
              expectedText={expectedText}
              surahNumber={surahNumber}
              ayahNumber={ayahNumber}
              endAyahNumber={endAyahNumber}
              onAnalysisComplete={handleAudioAnalysis}
              onRecordingReset={() => {
                invalidateAlignment();
                setRecognizedText("");
              }}
            />
          )}

          <form onSubmit={handleSubmit}>
            <label htmlFor="recognizedText">
              النص المتعرف عليه من التلاوة
            </label>

            <textarea
              id="recognizedText"
              rows={4}
              value={recognizedText}
              onChange={(event) => {
                invalidateAlignment();
                setRecognizedText(event.target.value);
              }}
              placeholder="أدخل نص التلاوة هنا..."
              required
            />

            <button
              type="submit"
              disabled={submitting || !hasSelection}
            >
              <GitCompareArrows size={18} />
              {submitting ? "جاري المقارنة..." : "مقارنة النصوص"}
            </button>
          </form>

          {error && (
            <p className="form-error" role="alert">{error}</p>
          )}

          {recitationSessionId && (
            <p role="status">
              تم حفظ التلاوة، ويمكن ربطها بخطة حفظ.
            </p>
          )}

          {recitationSessionId && (
            <section aria-label="ربط التلاوة بخطة حفظ">
              <h2>ربط التلاوة بخطة حفظ</h2>
              {plansError && <p role="alert">{plansError}</p>}
              <form onSubmit={handleLinkSession}>
                <label htmlFor="memorizationPlan">خطة الحفظ</label>
                <select
                  id="memorizationPlan"
                  value={selectedPlanId}
                  onChange={(event) => setSelectedPlanId(event.target.value)}
                  disabled={linking || linkSuccess}
                  required
                >
                  <option value="">اختر خطة متوافقة</option>
                  {memorizationPlans
                    .filter((plan) =>
                      plan.surah_number === surahNumber &&
                      plan.start_ayah <= ayahNumber &&
                      plan.end_ayah >= endAyahNumber
                    )
                    .map((plan) => (
                      <option key={plan.id} value={plan.id}>
                        الآيات {plan.start_ayah}–{plan.end_ayah}
                      </option>
                    ))}
                </select>

                <label htmlFor="sessionType">نوع الجلسة</label>
                <select
                  id="sessionType"
                  value={sessionType}
                  onChange={(event) =>
                    setSessionType(event.target.value as SessionType)
                  }
                  disabled={linking || linkSuccess}
                >
                  <option value="memorization">حفظ</option>
                  <option value="revision">مراجعة</option>
                </select>

                <label htmlFor="sessionResult">نتيجة الجلسة</label>
                <select
                  id="sessionResult"
                  value={sessionResult}
                  onChange={(event) =>
                    setSessionResult(event.target.value as SessionResult)
                  }
                  disabled={linking || linkSuccess}
                >
                  <option value="needs_review">تحتاج مراجعة</option>
                  <option value="completed">مكتملة</option>
                  <option value="incomplete">غير مكتملة</option>
                </select>

                <button
                  type="submit"
                  disabled={!selectedPlanId || linking || linkSuccess}
                >
                  {linking ? "جاري الحفظ..." : linkSuccess ? "تم الربط" : "حفظ الجلسة"}
                </button>
              </form>

              {linkError && <p role="alert">{linkError}</p>}
              {linkSuccess && (
                <p role="status">تم ربط التلاوة بخطة الحفظ بنجاح.</p>
              )}
            </section>
          )}

          {result && (
            <section className="alignment-results" aria-live="polite">
              <h2>نتيجة المقارنة النصية</h2>

              <div className="alignment-stats">
                <div>
                  <strong>{result.expected_word_count}</strong>
                  <span>الكلمات المتوقعة</span>
                </div>
                <div>
                  <strong>{result.recognized_word_count}</strong>
                  <span>الكلمات المتعرف عليها أو المدخلة</span>
                </div>
                <div>
                  <strong>{result.matched_word_count}</strong>
                  <span>الكلمات المتطابقة</span>
                </div>
              </div>

              {result.issues.length === 0 ? (
                <p>لم تُرصد اختلافات نصية بعد التطبيع.</p>
              ) : (
                <div className="alignment-issues">
                  {result.issues.map((issue, index) => (
                    <article key={index} className="alignment-issue">
                      <strong>{issueLabels[issue.operation]}</strong>
                      <p>
                        المتوقع: {issue.expected_word ?? "—"}
                      </p>
                      <p>
                        المتعرف عليه أو المُدخل: {issue.recognized_word ?? "—"}
                      </p>
                    </article>
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      </section>
    </main>
  );
}
