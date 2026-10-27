"""Download and verify the pinned local Quran dataset."""

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

SOURCE_URL = "https://api.alquran.cloud/v1/quran/ar.uthmani"
EDITION = "quran-uthmani-quran-academy"

EXPECTED_SHA256 = (
    "dd23407f608dd6bcb56ce8e2a2c28b6bdde38e3e7560ce0fba305365ce6584fe"
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "backend/data/quran/uthmani.json"


def build_dataset(payload: dict) -> dict:
    if payload.get("code") != 200:
        raise ValueError("Unexpected API response")

    quran = payload.get("data")
    if not isinstance(quran, dict):
        raise ValueError("Missing Quran data")

    if quran.get("edition", {}).get("identifier") != EDITION:
        raise ValueError("Unexpected Quran edition")

    surahs = quran.get("surahs")
    if not isinstance(surahs, list) or len(surahs) != 114:
        raise ValueError("Expected 114 surahs")

    result = []
    total = 0

    for number, surah in enumerate(surahs, start=1):
        if surah.get("number") != number:
            raise ValueError("Invalid surah numbering")

        ayahs = surah.get("ayahs")
        if not isinstance(ayahs, list) or not ayahs:
            raise ValueError("Missing ayahs")

        verses = []

        for ayah_number, ayah in enumerate(ayahs, start=1):
            if ayah.get("numberInSurah") != ayah_number:
                raise ValueError("Invalid ayah numbering")

            text = ayah.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Invalid ayah text")

            verses.append({
                "number": ayah_number,
                "text": text,
            })
            total += 1

        result.append({
            "number": number,
            "name": surah["name"],
            "ayahs": verses,
        })

    if total != 6236:
        raise ValueError(f"Unexpected ayah count: {total}")

    return {
        "source": SOURCE_URL,
        "edition": EDITION,
        "surahs": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify the existing local dataset without downloading",
    )
    args = parser.parse_args()

    if args.verify_only:
        if not OUTPUT.is_file():
            print("ERROR: Dataset not found", file=sys.stderr)
            return 1
        content = OUTPUT.read_bytes()
    else:
        if OUTPUT.exists():
            print("Dataset already exists; use --verify-only.")
            return 1

        try:
            with urllib.request.urlopen(
                SOURCE_URL, timeout=30
            ) as response:
                payload = json.load(response)

            dataset = build_dataset(payload)
            content = (
                json.dumps(
                    dataset,
                    ensure_ascii=False,
                    indent=2,
                ) + "\n"
            ).encode("utf-8")
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    digest = hashlib.sha256(content).hexdigest()

    if digest != EXPECTED_SHA256:
        print(
            "ERROR: Quran dataset checksum mismatch. "
            "File was not written.",
            file=sys.stderr,
        )
        return 1

    if not args.verify_only:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(content)

    print("Quran dataset verification: PASSED")
    print("SHA-256:", digest)
    print("Location:", OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
