import { getCsrfToken } from "../../auth/api/auth";
import { apiRequest } from "../../../services/api";

export interface QuranLocation {
  surah_number: number;
  ayah_number: number;
}

export interface Bookmark extends QuranLocation {
  created_at: string;
}

export interface BookmarkList {
  items: Bookmark[];
  count: number;
}

export interface ReadingProgress extends QuranLocation {
  updated_at: string;
}

const BASE = "/api/v1/quran";

export function listBookmarks(): Promise<BookmarkList> {
  return apiRequest<BookmarkList>(`${BASE}/bookmarks`);
}

export async function addBookmark(
  surahNumber: number,
  ayahNumber: number,
): Promise<Bookmark> {
  const csrf = await getCsrfToken();

  return apiRequest<Bookmark>(
    `${BASE}/bookmarks/${surahNumber}/${ayahNumber}`,
    {
      method: "PUT",
      headers: { "X-CSRF-Token": csrf },
    },
  );
}

export async function removeBookmark(
  surahNumber: number,
  ayahNumber: number,
): Promise<{ deleted: boolean }> {
  const csrf = await getCsrfToken();

  return apiRequest<{ deleted: boolean }>(
    `${BASE}/bookmarks/${surahNumber}/${ayahNumber}`,
    {
      method: "DELETE",
      headers: { "X-CSRF-Token": csrf },
    },
  );
}

export function getReadingProgress(): Promise<ReadingProgress | null> {
  return apiRequest<ReadingProgress | null>(`${BASE}/progress`);
}

export async function saveReadingProgress(
  location: QuranLocation,
): Promise<ReadingProgress> {
  const csrf = await getCsrfToken();

  return apiRequest<ReadingProgress>(`${BASE}/progress`, {
    method: "PUT",
    headers: { "X-CSRF-Token": csrf },
    body: JSON.stringify(location),
  });
}
