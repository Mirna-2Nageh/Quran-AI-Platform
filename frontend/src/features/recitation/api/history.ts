import type { AlignmentResponse } from "./recitation";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL !== undefined ? import.meta.env.VITE_API_BASE_URL : "http://localhost:8001";

export interface RecitationHistoryItem {
  id: string;
  surah_number: number;
  ayah_number: number;
  end_ayah_number?: number;
  expected_text: string;
  recognized_text: string;
  alignment: AlignmentResponse;
  analysis_type: "word_level_asr_alignment";
  tajweed_analyzed: false;
  created_at: string;
}

export interface RecitationHistoryResponse {
  items: RecitationHistoryItem[];
  count: number;
}

export async function getRecitationHistory(
  limit = 20,
): Promise<RecitationHistoryResponse> {
  if (!Number.isInteger(limit) || limit < 1 || limit > 50) {
    throw new Error("History limit must be between 1 and 50");
  }

  const response = await fetch(
    `${API_BASE_URL}/api/v1/recitation/history?limit=${limit}`,
    {
      method: "GET",
      credentials: "include",
    },
  );

  if (!response.ok) {
    let message = `Failed to load recitation history (${response.status})`;

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
      // Preserve the HTTP status error.
    }

    throw new Error(message);
  }

  return response.json() as Promise<RecitationHistoryResponse>;
}
