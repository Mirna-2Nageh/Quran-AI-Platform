import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowRight, BookOpen } from "lucide-react";
import {
  getSurah,
  getAyahTafsir,
  type AyahTafsir,
  type SurahDetail,
} from "../api/quran";

export function SurahDetailPage() {
  const { number } = useParams();
  const surahNumber = Number(number);

  const [surah, setSurah] = useState<SurahDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedAyah, setSelectedAyah] = useState<string | null>(null);
  const [tafsir, setTafsir] = useState<AyahTafsir | null>(null);
  const [tafsirLoading, setTafsirLoading] = useState(false);
  const [tafsirError, setTafsirError] = useState("");
  const [tafsirRetry, setTafsirRetry] = useState(0);

  useEffect(() => {
    if (selectedAyah === null) return;

    let cancelled = false;

    getAyahTafsir(surahNumber, Number(selectedAyah.split(":")[1]))
      .then((data) => {
        if (!cancelled) setTafsir(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setTafsirError(
            err instanceof Error ? err.message : "تعذر تحميل التفسير",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setTafsirLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [surahNumber, selectedAyah, tafsirRetry]);

  function toggleTafsir(ayahNumber: number) {
    const ayahKey = `${surahNumber}:${ayahNumber}`;

    if (selectedAyah === ayahKey) {
      setSelectedAyah(null);
      return;
    }

    setTafsir(null);
    setTafsirError("");
    setTafsirLoading(true);
    setSelectedAyah(ayahKey);
  }

  function retryTafsir() {
    setTafsir(null);
    setTafsirError("");
    setTafsirLoading(true);
    setTafsirRetry((value) => value + 1);
  }


  useEffect(() => {
    if (!Number.isInteger(surahNumber) || surahNumber < 1 || surahNumber > 114) {
      return;
    }

    let cancelled = false;

    getSurah(surahNumber)
      .then((data) => {
        if (!cancelled) setSurah(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "تعذر تحميل السورة");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [surahNumber]);

  if (!Number.isInteger(surahNumber) || surahNumber < 1 || surahNumber > 114) {
    return (
      <main className="quran-content" dir="rtl">
        <h1>رقم السورة غير صحيح</h1>
        <Link to="/quran">العودة إلى فهرس السور</Link>
      </main>
    );
  }

  return (
    <main className="quran-page" dir="rtl">
      <header className="quran-header">
        <Link to="/quran" className="back-link">
          <ArrowRight size={18} />
          فهرس السور
        </Link>

        <div className="brand">
          <BookOpen size={25} />
          <strong>Quran AI</strong>
        </div>
      </header>

      <section className="quran-content surah-detail">
        {loading && <p role="status">جاري تحميل السورة...</p>}
        {error && <p className="form-error" role="alert">{error}</p>}

        {surah && !loading && !error && (
          <>
            <div className="surah-title">
              <p className="eyebrow">القرآن الكريم</p>
              <h1>{surah.name}</h1>
              <p className="muted">
                {surah.numberOfAyahs} آية
              </p>
            </div>

            <div className="ayah-list">
              {surah.ayahs.map((ayah) => (
                <article className="ayah-row" key={ayah.numberInSurah}>
                  <span className="ayah-badge">
                    {ayah.numberInSurah}
                  </span>
                  <div className="ayah-body">
                    <p className="ayah-text" lang="ar">
                      {ayah.text}
                    </p>

                    <Link
                      to={`/recitation?surah=${surahNumber}&ayah=${ayah.numberInSurah}`}
                      className="ayah-practice-link"
                    >
                      ابدأ تسميع هذه الآية
                    </Link>

                    <button
                      type="button"
                      className="tafsir-toggle"
                      aria-expanded={selectedAyah === `${surahNumber}:${ayah.numberInSurah}`}
                      onClick={() => toggleTafsir(ayah.numberInSurah)}
                    >
                      {selectedAyah === `${surahNumber}:${ayah.numberInSurah}`
                        ? "إخفاء التفسير"
                        : "عرض التفسير"}
                    </button>

                    {selectedAyah === `${surahNumber}:${ayah.numberInSurah}` && (
                      <section className="tafsir-panel" aria-label="تفسير الآية">
                        {tafsirLoading && (
                          <p role="status">جاري تحميل التفسير...</p>
                        )}

                        {tafsirError && (
                          <div>
                            <p className="form-error" role="alert">
                              {tafsirError}
                            </p>
                            <button type="button" onClick={retryTafsir}>
                              إعادة المحاولة
                            </button>
                          </div>
                        )}

                        {tafsir && !tafsirLoading && !tafsirError && (
                          <>
                            <h3>{tafsir.edition.name}</h3>
                            <p lang="ar">{tafsir.text}</p>
                          </>
                        )}
                      </section>
                    )}
                  </div>
                </article>
              ))}
            </div>

            <nav className="surah-navigation" aria-label="التنقل بين السور">
              {surahNumber > 1 ? (
                <Link to={`/quran/${surahNumber - 1}`}>
                  السورة السابقة
                </Link>
              ) : <span />}

              <Link to="/quran">جميع السور</Link>

              {surahNumber < 114 ? (
                <Link to={`/quran/${surahNumber + 1}`}>
                  السورة التالية
                </Link>
              ) : <span />}
            </nav>
          </>
        )}
      </section>
    </main>
  );
}
