"""Tests for live memorization word alignment."""

from app.ai.alignment import align_words
from app.services.live_correction import correct_chunk


def test_partial_recitation_does_not_mark_future_words_missing():
    expected = "الحمد لله رب العالمين"
    recognized = "الحمد لله"

    result = align_words(
        expected_text=" ".join(expected.split()[:2]),
        recognized_text=recognized,
    )

    assert result.matched_word_count == 2
    assert result.issues == []


def test_substitution_is_reported():
    result = align_words("الحمد لله", "الحمد الرحمن")

    assert result.matched_word_count == 1
    assert len(result.issues) == 1
    assert result.issues[0].operation == "substitution"


def test_missing_word_is_reported():
    result = align_words("الحمد لله رب", "الحمد رب")

    assert any(issue.operation == "deletion" for issue in result.issues)


def test_repeated_words_do_not_crash_alignment():
    result = align_words("الله الله رب", "الله رب")

    assert result.matched_word_count == 2
    assert len(result.issues) == 1
    assert result.issues[0].operation == "deletion"




def test_empty_chunk_does_not_advance():
    result = correct_chunk("الحمد لله رب", "", 0)

    assert result.next_word_index == 0
    assert result.word_feedback == []


def test_invalid_start_index_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        correct_chunk("الحمد لله", "الحمد", 5)


def test_complete_correct_chunk_can_advance():
    result = correct_chunk("الحمد لله رب", "الحمد لله", 0)

    assert result.matched_word_count == 2
    assert result.next_word_index == 2


def test_missing_middle_word_does_not_mark_wrong_position_matched():
    result = correct_chunk("الحمد لله رب العالمين", "الحمد رب العالمين", 0)

    feedback = {item["index"]: item for item in result.word_feedback}

    assert feedback[1]["status"] == "review"
    assert result.next_word_index <= 1


def test_extra_recognized_word_does_not_skip_expected_words():
    result = correct_chunk("الحمد لله رب", "الحمد زيادة لله", 0)

    assert result.next_word_index <= 1


def test_missing_word_preserves_later_match():
    result = correct_chunk(
        "الحمد لله رب العالمين",
        "الحمد رب العالمين",
    )

    feedback = {item["index"]: item for item in result.word_feedback}

    assert feedback[1]["status"] == "review"
    assert feedback[2]["status"] == "matched"
    assert feedback[3]["status"] == "matched"
    assert result.next_word_index == 1


def test_extra_word_preserves_later_match():
    result = correct_chunk(
        "الحمد لله رب",
        "الحمد زيادة لله رب",
    )

    feedback = {item["index"]: item for item in result.word_feedback}

    assert feedback[1]["status"] == "matched"
    assert feedback[2]["status"] == "matched"
    assert result.next_word_index == 1


def test_unspoken_trailing_words_are_pending():
    result = correct_chunk(
        "الحمد لله رب العالمين",
        "الحمد لله",
    )

    statuses = {
        item["index"]: item["status"]
        for item in result.word_feedback
    }

    assert statuses[0] == "matched"
    assert statuses[1] == "matched"
    assert statuses[2] == "pending"
    assert statuses[3] == "pending"


def test_complete_recitation_has_no_pending_words():
    result = correct_chunk(
        "الحمد لله رب",
        "الحمد لله رب",
    )

    assert all(
        item["status"] == "matched"
        for item in result.word_feedback
    )
    assert result.has_more_words is False


def test_pending_words_do_not_count_as_reviewed():
    result = correct_chunk(
        "الحمد لله رب العالمين",
        "الحمد لله",
    )

    assert result.reviewed_word_count == 2
    assert result.next_word_index == 2
    assert result.has_more_words is True


def test_empty_recitation_has_no_reviewed_words():
    result = correct_chunk(
        "الحمد لله رب العالمين",
        "",
    )

    assert result.reviewed_word_count == 0
    assert result.next_word_index == 0
    assert result.has_more_words is True
