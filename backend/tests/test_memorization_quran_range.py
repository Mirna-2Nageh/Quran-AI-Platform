"""Tests for memorization Quran range validation."""

import pytest
from app.services.quran_text import (
    QuranTextError,
    validate_quran_range,
)


def test_valid_single_ayah():
    assert validate_quran_range(1, 1, 1) == 1


def test_valid_full_surah():
    assert validate_quran_range(1, 1, 7) == 7


def test_valid_range_longer_than_recitation_limit():
    assert validate_quran_range(2, 1, 20) == 20


@pytest.mark.parametrize(
    "surah,start,end",
    [
        (0, 1, 1),
        (115, 1, 1),
        (1, 0, 1),
        (1, 3, 2),
        (1, 1, 8),
        (114, 1, 7),
    ],
)
def test_invalid_ranges(surah, start, end):
    with pytest.raises(QuranTextError):
        validate_quran_range(surah, start, end)
