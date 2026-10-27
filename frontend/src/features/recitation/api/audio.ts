import { getCsrfToken } from "../../auth/api/auth";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001";

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

export interface AudioAnalysisResponse {
  session_id: string;
  recognized_text: string;
  alignment: import("./recitation").AlignmentResponse;
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
