import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, Search } from "lucide-react";
import { getSurahs, type Surah } from "../api/quran";
import { SurahCard } from "../components/SurahCard";

export function QuranReaderPage() {
  const [surahs, setSurahs] = useState<Surah[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getSurahs()
      .then(setSurahs)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "تعذر تحميل السور"),
      )
      .finally(() => setLoading(false));
  }, []);

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
