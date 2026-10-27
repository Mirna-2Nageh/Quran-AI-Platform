"""Read validated Quran text from the local Uthmani dataset."""

import json
from functools import lru_cache
from pathlib import Path


DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "quran"
    / "uthmani.json"
)


class QuranTextError(ValueError):
    """Invalid surah or ayah reference."""


class QuranDatasetError(QuranTextError):
    """Missing, malformed, or unexpected Quran dataset."""


@lru_cache(maxsize=1)
def load_quran() -> dict:
    """Load and structurally validate the local Quran dataset."""

    try:
        with DATASET_PATH.open(encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise QuranDatasetError("Quran dataset unavailable") from exc

    if data.get("edition") != "quran-uthmani-quran-academy":
        raise QuranDatasetError("Unexpected Quran edition")

    surahs = data.get("surahs")

    if not isinstance(surahs, list) or len(surahs) != 114:
        raise QuranDatasetError("Invalid Quran dataset structure")

    total_ayahs = 0

    for surah_number, surah in enumerate(surahs, start=1):
        if surah.get("number") != surah_number:
            raise QuranDatasetError("Invalid surah numbering")

        ayahs = surah.get("ayahs")

        if not isinstance(ayahs, list) or not ayahs:
            raise QuranDatasetError("Invalid ayah collection")

        for ayah_number, ayah in enumerate(ayahs, start=1):
            if ayah.get("number") != ayah_number:
                raise QuranDatasetError("Invalid ayah numbering")

            text = ayah.get("text")

            if not isinstance(text, str) or not text.strip():
                raise QuranDatasetError("Invalid ayah text")

            total_ayahs += 1

    if total_ayahs != 6236:
        raise QuranDatasetError("Unexpected total ayah count")

    return data


def get_quran_text(
    surah_number: int,
    start_ayah: int,
    end_ayah: int,
) -> str:
    """Return canonical text for a contiguous ayah range."""

    if not 1 <= surah_number <= 114:
        raise QuranTextError("Invalid surah number")

    if start_ayah < 1 or end_ayah < start_ayah:
        raise QuranTextError("Invalid ayah range")

    if end_ayah - start_ayah + 1 > 10:
        raise QuranTextError("Ayah range exceeds 10 verses")

    data = load_quran()
    ayahs = data["surahs"][surah_number - 1]["ayahs"]

    if end_ayah > len(ayahs):
        raise QuranTextError("Ayah number exceeds surah length")

    return " ".join(
        ayah["text"]
        for ayah in ayahs[start_ayah - 1 : end_ayah]
    )
