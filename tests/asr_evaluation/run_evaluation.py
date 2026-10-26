"""Reproducible batch evaluation for Quran ASR."""

import csv
import hashlib
import json
import subprocess
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from app.ai.alignment import normalize_arabic_word
from evaluate_baseline import edit_counts

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tests/asr_evaluation/manifest.json"
ASR_PYTHON = ROOT / ".venv-asr/bin/python"
ASR_SCRIPT = ROOT / "models/quran-asr-small/transcribe.py"
MODEL = ROOT / "models/quran-asr-small/model.int8.onnx"
OUTPUT_DIR = ROOT / "tests/asr_evaluation/results"


def words(text, normalized=False):
    result = text.split()
    if normalized:
        result = [normalize_arabic_word(w) for w in result]
    return [w for w in result if w]


def chars(text, normalized=False):
    if normalized:
        text = " ".join(words(text, True))
    return list(unicodedata.normalize("NFC", text).replace(" ", ""))


def calculate(reference, prediction, normalized=False):
    ref_words = words(reference, normalized)
    pred_words = words(prediction, normalized)
    ref_chars = chars(reference, normalized)
    pred_chars = chars(prediction, normalized)

    if not ref_words or not ref_chars:
        raise ValueError("Empty reference after normalization")

    wc = edit_counts(ref_words, pred_words)
    cc = edit_counts(ref_chars, pred_chars)

    return {
        "WER": wc["distance"] / len(ref_words),
        "CER": cc["distance"] / len(ref_chars),
        "S": wc["S"],
        "D": wc["D"],
        "I": wc["I"],
        "word_errors": wc["distance"],
        "reference_words": len(ref_words),
        "char_errors": cc["distance"],
        "reference_chars": len(ref_chars),
    }


def main():
    samples = json.loads(MANIFEST.read_text(encoding="utf-8"))

    if not samples:
        raise ValueError("Manifest is empty")

    ids = [sample["id"] for sample in samples]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate sample IDs")

    paths = []

    for sample in samples:
        if sample.get("verified") is not True:
            raise ValueError(f"Unverified sample: {sample['id']}")

        if not sample.get("reference", "").strip():
            raise ValueError(f"Missing reference: {sample['id']}")

        audio = (ROOT / sample["audio"]).resolve()

        if not audio.is_relative_to(ROOT.resolve()):
            raise ValueError(f"Audio path outside project: {sample['id']}")

        if not audio.is_file():
            raise FileNotFoundError(audio)

        paths.append(audio)

    for required in (ASR_PYTHON, ASR_SCRIPT, MODEL):
        if not required.is_file():
            raise FileNotFoundError(required)

    command = [
        str(ASR_PYTHON),
        str(ASR_SCRIPT),
        *[str(path) for path in paths],
    ]

    print(f"Running ASR on {len(samples)} verified samples...")

    start = time.perf_counter()
    process = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        check=True,
    )
    runtime = time.perf_counter() - start

    predictions = process.stdout.splitlines()

    if len(predictions) != len(samples):
        raise RuntimeError(
            f"Expected {len(samples)} predictions, "
            f"received {len(predictions)}"
        )

    if any(not prediction.strip() for prediction in predictions):
        raise RuntimeError("ASR returned an empty prediction")

    rows = []
    totals = {
        mode: {
            "word_errors": 0,
            "reference_words": 0,
            "char_errors": 0,
            "reference_chars": 0,
            "S": 0,
            "D": 0,
            "I": 0,
        }
        for mode in ("raw", "normalized")
    }

    for sample, prediction in zip(samples, predictions):
        row = {
            "id": sample["id"],
            "audio": sample["audio"],
            "reference": sample["reference"],
            "prediction": prediction.strip(),
            "verified": True,
        }

        for mode in ("raw", "normalized"):
            metrics = calculate(
                sample["reference"],
                prediction.strip(),
                normalized=(mode == "normalized"),
            )

            for key, value in metrics.items():
                row[f"{mode}_{key}"] = value

            for key in totals[mode]:
                totals[mode][key] += metrics[key]

        rows.append(row)

    summary = {}

    for mode, total in totals.items():
        summary[mode] = {
            "WER": total["word_errors"] / total["reference_words"],
            "CER": total["char_errors"] / total["reference_chars"],
            **total,
        }

    model_hash = hashlib.sha256(MODEL.read_bytes()).hexdigest()

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": str(MODEL.relative_to(ROOT)),
        "model_sha256": model_hash,
        "sample_count": len(samples),
        "batch_runtime_seconds": round(runtime, 4),
        "latency_note": (
            "Batch wall-clock runtime includes model loading "
            "and all sample inference; not per-sample latency."
        ),
        "summary": summary,
        "samples": rows,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_DIR / "latest.json"
    csv_path = OUTPUT_DIR / "latest.csv"

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nBatch runtime: {runtime:.3f}s")

    for mode, metrics in summary.items():
        print(
            f"{mode}: WER={metrics['WER']:.2%}, "
            f"CER={metrics['CER']:.2%}, "
            f"S={metrics['S']}, D={metrics['D']}, I={metrics['I']}"
        )

    print(f"\nJSON: {json_path.relative_to(ROOT)}")
    print(f"CSV:  {csv_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
