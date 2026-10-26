import { Link } from "react-router-dom";
import type { Surah } from "../api/quran";

interface Props {
  surah: Surah;
}

export function SurahCard({ surah }: Props) {
  return (
    <Link
      to={`/quran/${surah.number}`}
      className="surah-card"
      dir="rtl"
    >
      <span className="surah-number">{surah.number}</span>

      <div className="surah-info">
        <h3>{surah.name}</h3>
        <p>{surah.englishName}</p>
      </div>

      <span className="ayah-count">
        {surah.numberOfAyahs} آية
      </span>
    </Link>
  );
}
