import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, Search } from "lucide-react";
import { getSurahs, type Surah } from "../api/quran";
import { SurahCard } from "../components/SurahCard";
import { useAuth } from "../../auth/hooks/useAuth";
import {
  getReadingProgress,
  listBookmarks,
  type Bookmark,
  type ReadingProgress,
} from "../api/reading";


export function QuranReaderPage() {
  const { user } = useAuth();
  return <QuranReaderContent key={user?.id ?? "guest"} />;
}

function QuranReaderContent() {
  const [surahs, setSurahs] = useState<Surah[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { user } = useAuth();
  const userId = user?.id;
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [progress, setProgress] = useState<ReadingProgress | null>(null);
  const [readingLoading, setReadingLoading] = useState(Boolean(userId));
  const [readingError, setReadingError] = useState("");


  useEffect(() => {
    getSurahs()
      .then(setSurahs)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "تعذر تحميل السور"),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!userId) return;

    let cancelled = false;

    Promise.all([listBookmarks(), getReadingProgress()])
      .then(([savedBookmarks, savedProgress]) => {
        if (cancelled) return;
        setBookmarks(savedBookmarks.items);
        setProgress(savedProgress);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setReadingError(
            err instanceof Error ? err.message : "تعذر تحميل بيانات القراءة",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setReadingLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [userId]);

  const filteredSurahs = surahs.filter((surah) => {
    const query = search.trim().toLowerCase();
    return (
      surah.name.includes(query) ||
      surah.englishName.toLowerCase().includes(query) ||
      String(surah.number) === query
    );
  });

  return (
    <main className="quran-page" dir="rtl">
      <header className="quran-header">
        <Link to="/dashboard">العودة للوحة التحكم</Link>
        <div className="brand">
          <BookOpen size={25} />
          <strong>Quran AI</strong>
        </div>
      </header>

      <section className="quran-content">
        <p className="eyebrow">القرآن الكريم</p>
        <h1>فهرس السور</h1>
        <p className="muted">
          اختر سورة للبدء في القراءة والتعلم.
        </p>

        {user && (
          <section className="surah-detail" aria-label="قراءتي المحفوظة">
            <h2>متابعة القراءة</h2>

            {readingLoading && (
              <p role="status">جاري تحميل بيانات القراءة...</p>
            )}

            {readingError && (
              <p className="form-error" role="alert">{readingError}</p>
            )}

            {!readingLoading && progress && (
              <p>
                <Link
                  to={`/quran/${progress.surah_number}?ayah=${progress.ayah_number}`}
                >
                  متابعة من{" "}
                  {surahs.find((s) => s.number === progress.surah_number)?.name
                    ?? progress.surah_number}
                  {" "}— الآية {progress.ayah_number}
                </Link>
              </p>
            )}

            {!readingLoading && !progress && !readingError && (
              <p className="muted">لم يتم حفظ موضع قراءة بعد.</p>
            )}

            <h2>العلامات المرجعية</h2>

            {!readingLoading && bookmarks.length === 0 && !readingError && (
              <p className="muted">لا توجد آيات محفوظة بعد.</p>
            )}

            {bookmarks.map((bookmark) => (
              <p key={`${bookmark.surah_number}:${bookmark.ayah_number}`}>
                <Link
                  to={`/quran/${bookmark.surah_number}?ayah=${bookmark.ayah_number}`}
                >
                  {surahs.find((s) => s.number === bookmark.surah_number)?.name
                    ?? `سورة ${bookmark.surah_number}`}
                  {" "}— الآية {bookmark.ayah_number}
                </Link>
              </p>
            ))}
          </section>
        )}

        <div className="surah-search">
          <Search size={20} />
          <input
            type="search"
            placeholder="ابحث باسم السورة أو رقمها..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        {loading && <p role="status">جاري تحميل السور...</p>}

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        {!loading && !error && (
          <div className="surah-grid">
            {filteredSurahs.map((surah) => (
              <SurahCard key={surah.number} surah={surah} />
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
