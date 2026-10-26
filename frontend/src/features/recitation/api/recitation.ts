import { apiRequest } from "../../../services/api";

export type AlignmentOperation =
  | "substitution"
  | "deletion"
  | "insertion";

export interface AlignmentIssue {
  operation: AlignmentOperation;
  expected_word: string | null;
  recognized_word: string | null;
  expected_index: number | null;
  recognized_index: number | null;
}

export interface AlignmentResponse {
  expected_word_count: number;
  recognized_word_count: number;
  matched_word_count: number;
  issues: AlignmentIssue[];
}

export interface AlignmentRequest {
  expected_text: string;
  recognized_text: string;
}

export function alignRecitation(
  payload: AlignmentRequest,
): Promise<AlignmentResponse> {
  return apiRequest<AlignmentResponse>(
    "/api/v1/recitation/align",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
