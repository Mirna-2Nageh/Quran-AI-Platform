"""
Transcribe a recitation with quran-asr-small (sherpa-onnx, CPU).

    pip install sherpa-onnx soundfile numpy scipy
    python transcribe.py recitation.wav              # Uthmani letters, as the model writes
    python transcribe.py recitation.wav --standard   # standard (imla'i) spelling via spelling.json

Any sample rate / channel count works (converted to 16 kHz mono).
"""
import argparse
import json
import os
import sys

import numpy as np
import sherpa_onnx
import soundfile as sf
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    wave, sr = sf.read(path, dtype="float32", always_2d=True)
    wave = wave.mean(axis=1)
    if sr != 16000:
        g = np.gcd(sr, 16000)
        wave = resample_poly(wave, 16000 // g, sr // g).astype(np.float32)
    return wave


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", nargs="+")
    parser.add_argument("--standard", action="store_true", help="rewrite Uthmani spelling in standard spelling")
    parser.add_argument("--fp32", action="store_true", help="use model.onnx instead of model.int8.onnx")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Arabic on Windows consoles
    rec = sherpa_onnx.OfflineRecognizer.from_zipformer_ctc(
        model=os.path.join(HERE, "model.onnx" if args.fp32 else "model.int8.onnx"),
        tokens=os.path.join(HERE, "tokens.txt"), num_threads=2)
    table = json.load(open(os.path.join(HERE, "spelling.json"), encoding="utf-8")) if args.standard else {}
    for path in args.audio:
        stream = rec.create_stream()
        stream.accept_waveform(16000, load(path))
        rec.decode_stream(stream)
        words = stream.result.text.replace("▁", " ").split()
        print(" ".join(table.get(w, w) for w in words))


if __name__ == "__main__":
    main()
