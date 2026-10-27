import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  Clock3,
  History,
  RefreshCw,
} from "lucide-react";

import {
  getRecitationHistory,
  type RecitationHistoryItem,
} from "../api/history";
import { getSurahs } from "../../quran/api/quran";

const issueLabels = {
  substitution: "كلمة مختلفة",
  deletion: "كلمة ناقصة",
  insertion: "كلمة إضافية",
};

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "تاريخ غير متاح";
  }

  return new Intl.DateTimeFormat("ar-EG", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function RecitationHistoryPage() {
  const [items, setItems] = useState<RecitationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [surahNames, setSurahNames] = useState<Record<number, string>>({});

  const loadHistory = useCallback(async (signal?: AbortSignal) => {
    try {
      const response = await getRecitationHistory();

      if (signal?.aborted) return;

      setItems(response.items);
    } catch (err) {
      if (signal?.aborted) return;

      setError(
        err instanceof Error
          ? err.message
          : "تعذر تحميل سجل التلاوات",
      );
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    getRecitationHistory()
      .then((response) => {
        if (!controller.signal.aborted) {
          setItems(response.items);
        }
      })
      .catch((err: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : "تعذر تحميل سجل التلاوات",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    let cancelled = false;

    getSurahs()
      .then((surahs) => {
        if (cancelled) return;

        const names: Record<number, string> = {};

        for (const surah of surahs) {
          names[surah.number] = surah.name;
        }

        setSurahNames(names);
      })
      .catch(() => {
        // Keep the numeric surah label if names are unavailable.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const refreshHistory = () => {
    setLoading(true);
    setError("");
    void loadHistory();
  };

  return (
    <main className="quran-page" dir="rtl">
      <header className="quran-header">
        <Link to="/recitation">
          <ArrowRight size={18} />
          العودة للتلاوة
        </Link>

        <div className="brand">
          <BookOpen size={25} />
          <strong>Quran AI</strong>
        </div>
      </header>

      <section className="quran-content recitation-content">
        <p className="eyebrow">RECITATION HISTORY</p>

        <h1>سجل التلاوات</h1>

        <p className="muted">
          راجع محاولات التلاوة السابقة ونتائج مقارنة الكلمات.
          هذه النتائج لا تمثل تقييمًا لأحكام التجويد.
        </p>

        <button
          type="button"
          onClick={refreshHistory}
          disabled={loading}
        >
          <RefreshCw size={17} />
          تحديث السجل
        </button>

        {loading && (
          <p role="status">جاري تحميل سجل التلاوات...</p>
        )}

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        {!loading && !error && items.length === 0 && (
          <div className="recitation-panel">
            <History size={28} />
            <h2>لا توجد تلاوات محفوظة بعد</h2>
            <p className="muted">
              سجّل تلاوتك الأولى لتظهر هنا.
            </p>
            <Link to="/recitation">ابدأ التلاوة</Link>
          </div>
        )}

        {!loading && !error && items.length > 0 && (
          <div className="alignment-issues">
            {items.map((item) => (
              <article
                key={item.id}
                className="recitation-panel"
              >
                <h2>
                  سورة {surahNames[item.surah_number] ?? `رقم ${item.surah_number}`}
                  {" — "}
                  {(item.end_ayah_number ?? item.ayah_number) === item.ayah_number
                    ? `الآية ${item.ayah_number}`
                    : `الآيات ${item.ayah_number}–${item.end_ayah_number}`}
                </h2>

                <p className="muted">
                  <Clock3 size={16} />
                  {" "}
                  {formatDate(item.created_at)}
                </p>

                <div className="history-summary-stats">
                  <div>
                    <strong>{item.alignment.matched_word_count}</strong>
                    <span>كلمات متطابقة</span>
                  </div>
                  <div>
                    <strong>{item.alignment.expected_word_count}</strong>
                    <span>كلمات متوقعة</span>
                  </div>
                  <div>
                    <strong>{item.alignment.issues.length}</strong>
                    <span>اختلافات نصية</span>
                  </div>
                </div>

                <details className="history-details">
                  <summary>عرض تفاصيل التلاوة</summary>
                <h3>النص المتوقع</h3>
                <p className="history-quran-text" lang="ar" dir="rtl">{item.expected_text}</p>

                <h3>النص المتعرف عليه</h3>
                <p lang="ar">{item.recognized_text}</p>

                <div className="alignment-stats">
                  <div>
                    <strong>
                      {item.alignment.expected_word_count}
                    </strong>
                    <span>الكلمات المتوقعة</span>
                  </div>

                  <div>
                    <strong>
                      {item.alignment.recognized_word_count}
                    </strong>
                    <span>الكلمات المتعرف عليها</span>
                  </div>

                  <div>
                    <strong>
                      {item.alignment.matched_word_count}
                    </strong>
                    <span>الكلمات المتطابقة</span>
                  </div>
                </div>

                {item.alignment.issues.length === 0 ? (
                  <p>لم تُرصد اختلافات نصية بعد التطبيع.</p>
                ) : (
                  <div className="alignment-issues">
                    {item.alignment.issues.map((issue, index) => (
                      <div
                        key={index}
                        className="alignment-issue"
                      >
                        <strong>
                          {issueLabels[issue.operation]}
                        </strong>

                        <p>
                          المتوقع: {issue.expected_word ?? "—"}
                        </p>

                        <p>
                          المتعرف عليه:{" "}
                          {issue.recognized_word ?? "—"}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
                </details>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
