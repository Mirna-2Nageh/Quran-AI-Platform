"""Provisional Quran ASR evaluation using manually captured model outputs."""

import json
import unicodedata
from pathlib import Path

from app.ai.alignment import normalize_arabic_word


MANIFEST = Path("tests/asr_evaluation/manifest.json")

PREDICTIONS = {
    "001002": "الحمد لله رب العلمين",
    "001003": "الرحمن الرحيم",
    "001004": "ملك يوم الدين",
    "001005": "اياك نعبد واياك نستعين",
    "001006": "اهدنا الصرط المستقيم",
    "001007": "صرط الذين انعمت عليهم غير المغضوب عليهم ولا الضالين",
}


def edit_counts(reference, prediction):
    """Compute substitutions, deletions and insertions."""
    n, m = len(reference), len(prediction)

    dp = [[(0, 0, 0, 0) for _ in range(m + 1)] for _ in range(n + 1)]

    for i in range(1, n + 1):
        dp[i][0] = (i, 0, i, 0)

    for j in range(1, m + 1):
        dp[0][j] = (j, 0, 0, j)

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if reference[i - 1] == prediction[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
                continue

            sub = dp[i - 1][j - 1]
            delete = dp[i - 1][j]
            insert = dp[i][j - 1]

            candidates = [
                (sub[0] + 1, sub[1] + 1, sub[2], sub[3]),
                (delete[0] + 1, delete[1], delete[2] + 1, delete[3]),
                (insert[0] + 1, insert[1], insert[2], insert[3] + 1),
            ]
            dp[i][j] = min(candidates)

    distance, s, d, ins = dp[n][m]
    return {"distance": distance, "S": s, "D": d, "I": ins}


def tokens(text, normalized=False):
    words = text.split()
    if normalized:
        words = [normalize_arabic_word(w) for w in words]
    return [w for w in words if w]


def characters(text, normalized=False):
    if normalized:
        text = " ".join(tokens(text, normalized=True))
    return list(unicodedata.normalize("NFC", text).replace(" ", ""))


def main():
    samples = json.loads(MANIFEST.read_text(encoding="utf-8"))
    totals = {
        mode: {"words": 0, "word_errors": 0, "chars": 0, "char_errors": 0}
        for mode in ("raw", "normalized")
    }

    print("PROVISIONAL ASR BASELINE — UNVERIFIED REFERENCES")
    print("-" * 65)

    for sample in samples:
        sid = sample["id"]
        reference = sample["reference"]
        prediction = PREDICTIONS[sid]

        print(f"\nSample: {sid}")
        print("Reference:", reference)
        print("Prediction:", prediction)

        for mode in ("raw", "normalized"):
            normalized = mode == "normalized"

            ref_words = tokens(reference, normalized)
            pred_words = tokens(prediction, normalized)
            ref_chars = characters(reference, normalized)
            pred_chars = characters(prediction, normalized)

            word_counts = edit_counts(ref_words, pred_words)
            char_counts = edit_counts(ref_chars, pred_chars)

            wer = word_counts["distance"] / len(ref_words)
            cer = char_counts["distance"] / len(ref_chars)

            totals[mode]["words"] += len(ref_words)
            totals[mode]["word_errors"] += word_counts["distance"]
            totals[mode]["chars"] += len(ref_chars)
            totals[mode]["char_errors"] += char_counts["distance"]

            print(
                f"  {mode}: WER={wer:.2%}, CER={cer:.2%}, "
                f"S={word_counts['S']}, D={word_counts['D']}, "
                f"I={word_counts['I']}"
            )

    print("\n===== MICRO-AVERAGED DATASET RESULTS =====")

    for mode, data in totals.items():
        wer = data["word_errors"] / data["words"]
        cer = data["char_errors"] / data["chars"]

        print(
            f"{mode}: WER={wer:.2%}, CER={cer:.2%} "
            f"({data['word_errors']}/{data['words']} word errors)"
        )


if __name__ == "__main__":
    main()
