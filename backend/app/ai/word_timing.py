"""Approximate word timing derived from ASR character-token timestamps.

These timings are not forced alignment or pronunciation assessment.
"""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class WordTiming:
    word: str
    start_seconds: float
    end_seconds: float | None
    timing_type: str = "estimated_asr_word_boundary"


def estimate_word_timings(
    text: str,
    tokens: list[str],
    timestamps: list[float],
) -> list[WordTiming]:
    """Map ASR token starts to words, preserving standard spelling.

    A word's end is approximated by the next word's start.
    The final word has no reliable end boundary.
    """

    if len(tokens) != len(timestamps):
        raise ValueError("Token/timestamp count mismatch")

    if any(
        not isinstance(token, str) or len(token) != 1
        for token in tokens
    ):
        raise ValueError("Expected single-character ASR tokens")

    if any(
        isinstance(t, bool)
        or not isinstance(t, (int, float))
        or not isfinite(t)
        or t < 0
        for t in timestamps
    ):
        raise ValueError("Invalid timestamps")

    if any(a > b for a, b in zip(timestamps, timestamps[1:])):
        raise ValueError("Timestamps must be ordered")

    raw_words = []
    current_chars = []
    current_start = None

    for token, timestamp in zip(tokens, timestamps):
        if token.isspace():
            if current_chars:
                raw_words.append(
                    ("".join(current_chars), current_start)
                )
                current_chars = []
                current_start = None
            continue

        if current_start is None:
            current_start = float(timestamp)

        current_chars.append(token)

    if current_chars:
        raw_words.append(("".join(current_chars), current_start))

    standard_words = text.split()

    if len(raw_words) != len(standard_words):
        raise ValueError("Raw and standard word counts differ")

    result = []

    for index, word in enumerate(standard_words):
        start = raw_words[index][1]
        end = (
            raw_words[index + 1][1]
            if index + 1 < len(raw_words)
            else None
        )

        result.append(
            WordTiming(
                word=word,
                start_seconds=start,
                end_seconds=end,
            )
        )

    return result
