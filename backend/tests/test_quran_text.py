"""Tests for canonical Quran text retrieval."""

import pytest

from app.services.quran_text import (
    QuranTextError,
    get_quran_text,
    load_quran,
)


def test_dataset_structure():
    data = load_quran()

    assert data["edition"] == "quran-uthmani-quran-academy"
    assert len(data["surahs"]) == 114
    assert sum(len(s["ayahs"]) for s in data["surahs"]) == 6236


def test_single_ayah():
    text = get_quran_text(1, 1, 1)

    assert text
    assert text == load_quran()["surahs"][0]["ayahs"][0]["text"]


def test_multiple_ayahs():
    text = get_quran_text(1, 1, 3)
    ayahs = load_quran()["surahs"][0]["ayahs"]

    expected = " ".join(ayah["text"] for ayah in ayahs[:3])

    assert text == expected


@pytest.mark.parametrize(
    "surah,start,end",
    [
        (0, 1, 1),
        (115, 1, 1),
        (1, 0, 1),
        (1, 3, 2),
        (1, 1, 8),
        (2, 1, 11),
        (114, 1, 7),
    ],
)
def test_invalid_references(surah, start, end):
    with pytest.raises(QuranTextError):
        get_quran_text(surah, start, end)
