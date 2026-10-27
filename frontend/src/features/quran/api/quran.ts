export interface Surah {
  number: number;
  name: string;
  englishName: string;
  numberOfAyahs: number;
  revelationType: string;
}

export interface Ayah {
  number: number;
  numberInSurah: number;
  text: string;
}

export interface SurahDetail extends Surah {
  ayahs: Ayah[];
}

const QURAN_API_BASE = "https://api.alquran.cloud/v1";

async function quranRequest<T>(path: string): Promise<T> {
  const response = await fetch(`${QURAN_API_BASE}${path}`);

  if (!response.ok) {
    throw new Error(`Quran API request failed: ${response.status}`);
  }

  const payload: { code: number; data: T } = await response.json();

  if (payload.code !== 200) {
    throw new Error("Quran API returned an unsuccessful response");
  }

  return payload.data;
}

export function getSurahs(): Promise<Surah[]> {
  return quranRequest<Surah[]>("/surah");
}

export function getSurah(number: number): Promise<SurahDetail> {
  if (!Number.isInteger(number) || number < 1 || number > 114) {
    throw new Error("Invalid surah number");
  }

  return quranRequest<SurahDetail>(`/surah/${number}/ar.uthmani`);
}


export interface AyahTafsir {
  numberInSurah: number;
  text: string;
  edition: {
    identifier: string;
    name: string;
  };
}

export function getAyahTafsir(
  surahNumber: number,
  ayahNumber: number,
): Promise<AyahTafsir> {
  if (
    !Number.isInteger(surahNumber) ||
    surahNumber < 1 ||
    surahNumber > 114
  ) {
    throw new Error("Invalid surah number");
  }

  if (!Number.isInteger(ayahNumber) || ayahNumber < 1) {
    throw new Error("Invalid ayah number");
  }

  return quranRequest<AyahTafsir>(
    `/ayah/${surahNumber}:${ayahNumber}/ar.muyassar`,
  );
}
