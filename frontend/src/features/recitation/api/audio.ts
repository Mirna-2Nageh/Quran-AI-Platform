import { getCsrfToken } from "../../auth/api/auth";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "";

export interface AudioUploadResponse {
  message: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  stored: boolean;
  analyzed: boolean;
}

export async function uploadRecitationAudio(
  blob: Blob,
): Promise<AudioUploadResponse> {
  const csrfToken = await getCsrfToken();

  const formData = new FormData();

  const extension = blob.type.includes("ogg") ? "ogg" : "webm";

  formData.append(
    "audio",
    blob,
    `recitation.${extension}`,
  );

  const response = await fetch(
    `${API_BASE_URL}/api/v1/recitation/audio`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        "X-CSRF-Token": csrfToken,
      },
      body: formData,
    },
  );

  if (!response.ok) {
    let message = `Upload failed (${response.status})`;

    try {
      const data: unknown = await response.json();

      if (
        typeof data === "object" &&
        data !== null &&
        "detail" in data &&
        typeof data.detail === "string"
      ) {
        message = data.detail;
      }
    } catch {
      // Keep the HTTP status message.
    }

    throw new Error(message);
  }

  return response.json() as Promise<AudioUploadResponse>;
}

export interface WordTiming {
  word: string;
  start_seconds: number;
  end_seconds: number | null;
  timing_type: "estimated_asr_word_boundary";
}

export interface AudioAnalysisResponse {
  session_id: string;
  recognized_text: string;
  alignment: import("./recitation").AlignmentResponse;
  word_timings: WordTiming[];
  analysis_type: "word_level_asr_alignment";
  tajweed_analyzed: false;
}

export async function analyzeRecitationAudio(
  blob: Blob,
  expectedText: string,
  surahNumber: number,
  ayahNumber: number,
  endAyahNumber: number = ayahNumber,
): Promise<AudioAnalysisResponse> {
  const csrfToken = await getCsrfToken();

  const formData = new FormData();
  const extension = blob.type.includes("ogg") ? "ogg" : "webm";

  formData.append("audio", blob, `recitation.${extension}`);
  formData.append("expected_text", expectedText);
  formData.append("surah_number", String(surahNumber));
  formData.append("ayah_number", String(ayahNumber));
  formData.append("end_ayah_number", String(endAyahNumber));

  const response = await fetch(
    `${API_BASE_URL}/api/v1/recitation/analyze`,
    {
      method: "POST",
      credentials: "include",
      headers: {
        "X-CSRF-Token": csrfToken,
      },
      body: formData,
    },
  );

  if (!response.ok) {
    let message = `Audio analysis failed (${response.status})`;

    try {
      const data: unknown = await response.json();

      if (
        typeof data === "object" &&
        data !== null &&
        "detail" in data &&
        typeof data.detail === "string"
      ) {
        message = data.detail;
      }
    } catch {
      // Keep the HTTP status message.
    }

    throw new Error(message);
  }

  return response.json() as Promise<AudioAnalysisResponse>;
}

export interface LiveWordFeedback {
  index: number;
  word: string;
  status: "matched" | "review" | "pending";
  recognized_word: string | null;
}

export interface LiveCorrectionResponse {
  surah_number: number;
  ayah_number: number;
  recognized_text: string;
  alignment: import("./recitation").AlignmentResponse;
  word_feedback: LiveWordFeedback[];
  next_word_index: number;
  has_more_words: boolean;
  analysis_type: "chunk_based_word_alignment";
}

export async function analyzeLiveCorrectionChunk(
  blob: Blob,
  surahNumber: number,
  ayahNumber: number,
  startWordIndex = 0,
  sessionId?: string,
  chunkIndex?: number,
): Promise<LiveCorrectionResponse> {
  const csrfToken = await getCsrfToken();
  const formData = new FormData();

  const extension = blob.type.includes("ogg") ? "ogg" : "webm";

  formData.append("audio", blob, `chunk.${extension}`);
  formData.append("surah_number", String(surahNumber));
  formData.append("ayah_number", String(ayahNumber));
  formData.append("start_word_index", String(startWordIndex));
  if (sessionId !== undefined) formData.append("session_id", sessionId);
  if (chunkIndex !== undefined) formData.append("chunk_index", String(chunkIndex));

  const response = await fetch(
    `${API_BASE_URL}/api/v1/recitation/live-correction`,
    {
      method: "POST",
      credentials: "include",
      headers: { "X-CSRF-Token": csrfToken },
      body: formData,
    },
  );

  if (!response.ok) {
    let message = `Live correction failed (${response.status})`;

    try {
      const data: unknown = await response.json();
      if (
        typeof data === "object" &&
        data !== null &&
        "detail" in data &&
        typeof data.detail === "string"
      ) {
        message = data.detail;
      }
    } catch {
      // Keep HTTP status fallback.
    }

    throw new Error(message);
  }

  return response.json() as Promise<LiveCorrectionResponse>;
}

export interface LiveSessionStartResponse {
  session_id: string;
  status: "active";
}

export interface LiveSessionFinalizeResponse {
  session_id: string;
  recitation_session_id: string;
  status: "finalized";
}

async function liveSessionRequest<T>(
  path: string,
  body?: object,
): Promise<T> {
  const csrfToken = await getCsrfToken();
  const response = await fetch(`${API_BASE_URL}/api/v1/recitation/live-sessions${path}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "X-CSRF-Token": csrfToken,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  if (!response.ok) {
    let message = `Live session failed (${response.status})`;
    try {
      const data: { detail?: string } = await response.json();
      if (typeof data.detail === "string") message = data.detail;
    } catch {
      // Preserve HTTP fallback.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export function startLiveSession(surahNumber: number, ayahNumber: number) {
  return liveSessionRequest<LiveSessionStartResponse>("/start", {
    surah_number: surahNumber,
    ayah_number: ayahNumber,
  });
}

export function finalizeLiveSession(sessionId: string) {
  return liveSessionRequest<LiveSessionFinalizeResponse>(
    `/${encodeURIComponent(sessionId)}/finalize`,
  );
}
