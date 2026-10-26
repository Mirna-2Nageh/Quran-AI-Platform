"""Word-level alignment between expected Quran text and ASR transcription."""

import unicodedata
from dataclasses import dataclass
from typing import Literal

IssueType = Literal["substitution", "deletion", "insertion"]


@dataclass(frozen=True)
class AlignmentIssue:
    """A word-level difference between expected and recognized text.

    Indices are zero-based. A deletion means an expected word was omitted;
    an insertion means an unexpected word appeared in the transcription.
    """

    operation: IssueType
    expected_word: str | None
    recognized_word: str | None
    expected_index: int | None
    recognized_index: int | None


@dataclass(frozen=True)
class AlignmentResult:
    """Summary of the word-level alignment."""

    expected_word_count: int
    recognized_word_count: int
    matched_word_count: int
    issues: list[AlignmentIssue]


def normalize_arabic_word(word: str) -> str:
    """Normalize common Arabic writing differences for text comparison."""
    normalized = unicodedata.normalize("NFKC", word)
    # Normalize the verified Uthmani spelling of "صراط".
    # Preserve the written alef represented by the dagger alef.
    normalized = normalized.replace(
        "\u0635\u0650\u0631\u064e\u0670\u0637",
        "\u0635\u0631\u0627\u0637",
    )

    # Handle the verified Uthmani spelling of "العالمين".
    # The dagger alif represents the omitted written alef here.
    normalized = normalized.replace("\u0639\u064e\u0640\u0670\u0644", "\u0639\u0627\u0644")
    normalized = normalized.replace("\u0640", "")  # Tatweel

    # Ignore the Quranic end-of-ayah marker.
    normalized = normalized.replace("\u06dd", "")

    normalized = normalized.translate(
        str.maketrans(
            {
                "\u0622": "\u0627",  # Alef with madda
                "\u0623": "\u0627",  # Alef with hamza above
                "\u0625": "\u0627",  # Alef with hamza below
                "\u0671": "\u0627",  # Alef wasla
                "\u0649": "\u064a",  # Alef maqsura
                "\u06cc": "\u064a",  # Farsi Yeh -> Arabic Yeh
            }
        )
    )

    # Ignore Arabic diacritics and punctuation during comparison.
    normalized = "".join(
        char for char in normalized if unicodedata.category(char)[0] not in {"M", "P"}
    )
    return normalized


def _tokenize(text: str) -> list[tuple[str, str]]:
    """Return (original token, normalized token) pairs."""
    tokens: list[tuple[str, str]] = []

    for original in text.split():
        normalized = normalize_arabic_word(original)
        if normalized:
            tokens.append((original, normalized))

    return tokens


def align_words(expected_text: str, recognized_text: str) -> AlignmentResult:
    """Align recognized words with expected words and report differences.

    This is textual alignment only; it does not assess pronunciation or Tajweed.
    """
    expected = _tokenize(expected_text)
    recognized = _tokenize(recognized_text)

    expected_normalized = [token[1] for token in expected]
    recognized_normalized = [token[1] for token in recognized]

    n = len(expected)
    m = len(recognized)

    # dp[i][j] is the minimum edit cost for the first i and j words.
    dp = [[0] * (m + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        dp[i][0] = i

    for j in range(1, m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            substitution_cost = (
                0 if expected_normalized[i - 1] == recognized_normalized[j - 1] else 1
            )
            dp[i][j] = min(
                dp[i - 1][j] + 1,  # Missing expected word
                dp[i][j - 1] + 1,  # Extra recognized word
                dp[i - 1][j - 1] + substitution_cost,
            )

    issues: list[AlignmentIssue] = []
    matched_word_count = 0
    i, j = n, m

    while i > 0 or j > 0:
        is_match = (
            i > 0
            and j > 0
            and expected_normalized[i - 1] == recognized_normalized[j - 1]
            and dp[i][j] == dp[i - 1][j - 1]
        )

        deletion_is_tied = i > 0 and dp[i][j] == dp[i - 1][j] + 1

        # Prefer matching the earlier expected occurrence when repeated words
        # create equally optimal alignment paths.
        if is_match and deletion_is_tied:
            issues.append(
                AlignmentIssue(
                    operation="deletion",
                    expected_word=expected[i - 1][0],
                    recognized_word=None,
                    expected_index=i - 1,
                    recognized_index=None,
                )
            )
            i -= 1
        elif is_match:
            matched_word_count += 1
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            issues.append(
                AlignmentIssue(
                    operation="substitution",
                    expected_word=expected[i - 1][0],
                    recognized_word=recognized[j - 1][0],
                    expected_index=i - 1,
                    recognized_index=j - 1,
                )
            )
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            issues.append(
                AlignmentIssue(
                    operation="deletion",
                    expected_word=expected[i - 1][0],
                    recognized_word=None,
                    expected_index=i - 1,
                    recognized_index=None,
                )
            )
            i -= 1
        else:
            issues.append(
                AlignmentIssue(
                    operation="insertion",
                    expected_word=None,
                    recognized_word=recognized[j - 1][0],
                    expected_index=None,
                    recognized_index=j - 1,
                )
            )
            j -= 1

    issues.reverse()

    return AlignmentResult(
        expected_word_count=n,
        recognized_word_count=m,
        matched_word_count=matched_word_count,
        issues=issues,
    )
