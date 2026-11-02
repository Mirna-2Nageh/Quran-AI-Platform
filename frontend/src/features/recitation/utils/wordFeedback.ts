import type {
  AlignmentResponse,
} from "../api/recitation";

export type WordFeedbackStatus =
  | "matched"
  | "substituted"
  | "missing";

export interface WordFeedback {
  index: number;
  word: string;
  status: WordFeedbackStatus;
  recognizedWord: string | null;
  recognizedIndex: number | null;
}

export interface ExtraWordFeedback {
  word: string;
  recognizedIndex: number;
}

export interface WordFeedbackResult {
  words: WordFeedback[];
  extraWords: ExtraWordFeedback[];
  matchPercentage: number;
  canHighlight: boolean;
}

export function tokenizeExpectedWords(text: string): string[] {
  return text
    .trim()
    .split(/\s+/)
    .filter((word) => {
      const normalized = word
        .normalize("NFKC")
        .replace(/\u0640/g, "")
        .replace(/\u06dd/g, "")
        .replace(/[\p{M}\p{P}]/gu, "");

      return normalized.length > 0;
    });
}

function normalizeForComparison(word: string): string {
  return word
    .normalize("NFKC")
    .replace(/\u0640/g, "")
    .replace(/\u06dd/g, "")
    .replace(/[\p{M}\p{P}]/gu, "");
}

export function buildWordFeedback(
  expectedText: string,
  alignment: AlignmentResponse,
): WordFeedbackResult {
  const expectedWords = tokenizeExpectedWords(expectedText);
  const canHighlight =
    expectedWords.length === alignment.expected_word_count &&
    alignment.issues.every((issue) => {
      if (issue.operation === "insertion") return true;
      if (issue.expected_index === null || issue.expected_word === null) {
        return false;
      }

      const displayed = expectedWords[issue.expected_index];
      if (!displayed) return false;

      return normalizeForComparison(displayed) ===
        normalizeForComparison(issue.expected_word);
    });

  const words: WordFeedback[] = expectedWords.map((word, index) => ({
    index,
    word,
    status: "matched",
    recognizedWord: null,
    recognizedIndex: null,
  }));

  const extraWords: ExtraWordFeedback[] = [];

  for (const issue of alignment.issues) {
    if (issue.operation === "insertion") {
      if (
        issue.recognized_word !== null &&
        issue.recognized_index !== null
      ) {
        extraWords.push({
          word: issue.recognized_word,
          recognizedIndex: issue.recognized_index,
        });
      }
      continue;
    }

    if (!canHighlight) continue;

    const index = issue.expected_index;

    if (
      index === null ||
      index < 0 ||
      index >= words.length
    ) {
      continue;
    }

    const word = words[index];

    if (issue.operation === "substitution") {
      word.status = "substituted";
      word.recognizedWord = issue.recognized_word;
      word.recognizedIndex = issue.recognized_index;
    } else if (issue.operation === "deletion") {
      word.status = "missing";
      word.recognizedWord = null;
      word.recognizedIndex = null;
    }
  }

  const expectedCount = alignment.expected_word_count;

  const matchPercentage =
    expectedCount > 0
      ? Math.round(
          (alignment.matched_word_count / expectedCount) * 100,
        )
      : 0;

  return {
    words,
    extraWords,
    matchPercentage,
    canHighlight,
  };
}
