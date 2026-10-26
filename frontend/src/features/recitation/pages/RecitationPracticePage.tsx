import { AudioRecorder } from "../components/AudioRecorder";
import type { AudioAnalysisResponse } from "../api/audio";
import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { BookOpen, GitCompareArrows } from "lucide-react";

import { getSurah, type SurahDetail } from "../../quran/api/quran";
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
  const [surahNumber, setSurahNumber] = useState(1);
  const [surah, setSurah] = useState<SurahDetail | null>(null);
  const [ayahNumber, setAyahNumber] = useState(1);
  const [recognizedText, setRecognizedText] = useState("");
  const [result, setResult] = useState<AlignmentResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    getSurah(surahNumber)
      .then((data) => {
        if (!cancelled) {
          setSurah(data);
          setAyahNumber(1);
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
  }, [surahNumber]);

  const selectedAyah = surah?.ayahs.find(
    (ayah) => ayah.numberInSurah === ayahNumber,
  );

  function handleAudioAnalysis(
    analysis: AudioAnalysisResponse,
  ) {
    setRecognizedText(analysis.recognized_text);
    setResult(analysis.alignment);
    setError("");
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedAyah || !recognizedText.trim()) return;

    setError("");
    setSubmitting(true);
    setResult(null);

    try {
      const response = await alignRecitation({
        expected_text: selectedAyah.text,
        recognized_text: recognizedText,
      });
      setResult(response);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "تعذر مقارنة النصوص",
      );
    } finally {
      setSubmitting(false);
    }
  }

  function changeSurah(value: number) {
    setLoading(true);
    setError("");
    setResult(null);
    setRecognizedText("");
    setSurah(null);
    setSurahNumber(value);
  }

  function changeAyah(value: number) {
    setAyahNumber(value);
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
              رقم الآية
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
          </div>

          {loading && <p role="status">جاري تحميل الآيات...</p>}

          {selectedAyah && (
            <div className="expected-ayah" lang="ar">
              {selectedAyah.text}
            </div>
          )}

          {selectedAyah && (
            <AudioRecorder
              key={`${surahNumber}-${ayahNumber}`}
              expectedText={selectedAyah.text}
              surahNumber={surahNumber}
              ayahNumber={ayahNumber}
              onAnalysisComplete={handleAudioAnalysis}
              onRecordingReset={() => {
                setRecognizedText("");
                setResult(null);
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
              onChange={(event) =>
                setRecognizedText(event.target.value)
              }
              placeholder="أدخل نص التلاوة هنا..."
              required
            />

            <button
              type="submit"
              disabled={submitting || !selectedAyah}
            >
              <GitCompareArrows size={18} />
              {submitting ? "جاري المقارنة..." : "مقارنة النصوص"}
            </button>
          </form>

          {error && (
            <p className="form-error" role="alert">{error}</p>
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
