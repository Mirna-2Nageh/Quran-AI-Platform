"""Conservative word-level feedback for live memorization chunks."""

from dataclasses import dataclass

from app.ai.alignment import align_words


@dataclass(frozen=True)
class ChunkCorrection:
    matched_word_count: int
    reviewed_word_count: int
    next_word_index: int
    has_more_words: bool
    word_feedback: list[dict]


def correct_chunk(
    expected_text: str,
    recognized_text: str,
    start_word_index: int = 0,
) -> ChunkCorrection:
    words = expected_text.split()

    if not 0 <= start_word_index <= len(words):
        raise ValueError("Invalid start word index")

    recognized_words = recognized_text.split()

    if not recognized_words:
        return ChunkCorrection(
            matched_word_count=0,
            reviewed_word_count=0,
            next_word_index=start_word_index,
            has_more_words=start_word_index < len(words),
            word_feedback=[],
        )

    remaining = words[start_word_index:]

    if not remaining:
        raise ValueError("No expected words remaining")

    # Allow a small lookahead for missing expected words.
    window_size = min(len(remaining), len(recognized_words) + 2)
    candidate = remaining[:window_size]

    alignment = align_words(
        expected_text=" ".join(candidate),
        recognized_text=recognized_text,
    )

    issues = {
        issue.expected_index: issue
        for issue in alignment.issues
        if issue.expected_index is not None
    }

    # Trailing deletions are unresolved until later audio arrives.
    last_supported = max(
        (
            issue.expected_index
            for issue in alignment.issues
            if issue.expected_index is not None
            and issue.operation != "deletion"
        ),
        default=-1,
    )

    matched_indices = set(range(len(candidate))) - set(issues)

    if matched_indices:
        last_supported = max(last_supported, max(matched_indices))

    feedback = []

    for index, word in enumerate(candidate):
        issue = issues.get(index)

        if issue is None:
            status = "matched"
        elif issue.operation == "deletion" and index > last_supported:
            status = "pending"
        else:
            status = "review"

        feedback.append(
            {
                "index": start_word_index + index,
                "word": word,
                "status": status,
                "recognized_word": (
                    issue.recognized_word if issue else None
                ),
            }
        )

    issue_positions = [
        issue.expected_index
        if issue.expected_index is not None
        else (
            issue.recognized_index
            if issue.recognized_index is not None
            else 0
        )
        for issue in alignment.issues
        if issue.operation == "insertion"
        or (
            issue.expected_index is not None
            and feedback[issue.expected_index]["status"] == "review"
        )
    ]

    confirmed_count = (
        min(issue_positions)
        if issue_positions
        else sum(item["status"] == "matched" for item in feedback)
    )

    next_index = start_word_index + confirmed_count

    return ChunkCorrection(
        matched_word_count=alignment.matched_word_count,
        reviewed_word_count=sum(
            item["status"] != "pending" for item in feedback
        ),
        next_word_index=next_index,
        has_more_words=next_index < len(words),
        word_feedback=feedback,
    )
