"""Tests for approximate ASR word timing mapping."""

import pytest

from app.ai.word_timing import estimate_word_timings


def test_basic_word_timings():
    result = estimate_word_timings(
        text="بسم الله",
        tokens=list("بسم الله"),
        timestamps=[0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9],
    )

    assert len(result) == 2
    assert result[0].word == "بسم"
    assert result[0].start_seconds == pytest.approx(0.1)
    assert result[0].end_seconds == pytest.approx(0.6)
    assert result[1].word == "الله"
    assert result[1].start_seconds == pytest.approx(0.6)
    assert result[1].end_seconds is None


def test_repeated_words_preserve_order():
    result = estimate_word_timings(
        text="الله الله",
        tokens=list("الله الله"),
        timestamps=[0.1, 0.2, 0.3, 0.4, 0.5, 1.0, 1.1, 1.2, 1.3],
    )

    assert [item.word for item in result] == ["الله", "الله"]
    assert [item.start_seconds for item in result] == pytest.approx(
        [0.1, 1.0]
    )


def test_standard_spelling_can_differ():
    result = estimate_word_timings(
        text="العالمين",
        tokens=list("العلمين"),
        timestamps=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7],
    )

    assert len(result) == 1
    assert result[0].word == "العالمين"
    assert result[0].start_seconds == pytest.approx(0.1)
    assert result[0].end_seconds is None


def test_word_count_mismatch_rejected():
    with pytest.raises(ValueError, match="word counts differ"):
        estimate_word_timings(
            text="بسم الله",
            tokens=list("بسم"),
            timestamps=[0.1, 0.2, 0.3],
        )


def test_token_timestamp_count_mismatch():
    with pytest.raises(ValueError, match="count mismatch"):
        estimate_word_timings(
            text="بسم",
            tokens=["ب", "س", "م"],
            timestamps=[0.1],
        )


def test_multi_character_token_rejected():
    with pytest.raises(ValueError, match="single-character"):
        estimate_word_timings(
            text="بسم",
            tokens=["بسم"],
            timestamps=[0.1],
        )


@pytest.mark.parametrize("invalid", [-1, float("nan"), float("inf"), True])
def test_invalid_timestamp_rejected(invalid):
    with pytest.raises(ValueError, match="Invalid timestamps"):
        estimate_word_timings(
            text="ب",
            tokens=["ب"],
            timestamps=[invalid],
        )


def test_unsorted_timestamps_rejected():
    with pytest.raises(ValueError, match="ordered"):
        estimate_word_timings(
            text="بسم",
            tokens=["ب", "س", "م"],
            timestamps=[0.3, 0.1, 0.2],
        )


def test_empty_input_returns_empty_list():
    assert estimate_word_timings("", [], []) == []
