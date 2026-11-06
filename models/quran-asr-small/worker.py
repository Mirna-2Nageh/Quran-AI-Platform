"""Persistent local Quran ASR worker using newline-delimited JSON."""

import json
import sys
from pathlib import Path

import sherpa_onnx

from transcribe import HERE, load


def main():
    recognizer = sherpa_onnx.OfflineRecognizer.from_zipformer_ctc(
        model=str(Path(HERE) / "model.int8.onnx"),
        tokens=str(Path(HERE) / "tokens.txt"),
        num_threads=2,
    )
    spelling = json.loads(
        (Path(HERE) / "spelling.json").read_text(encoding="utf-8")
    )

    for line in sys.stdin:
        request_id = None
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("Invalid request")
            request_id = request.get("id")
            audio_path = request.get("audio_path")
            if not isinstance(audio_path, str) or not audio_path:
                raise ValueError("Invalid audio path")

            stream = recognizer.create_stream()
            stream.accept_waveform(16000, load(audio_path))
            recognizer.decode_stream(stream)

            result = stream.result
            words = result.text.replace("▁", " ").split()
            text = " ".join(spelling.get(word, word) for word in words)

            response = {
                "id": request_id,
                "ok": True,
                "text": text,
                "tokens": list(result.tokens),
                "timestamps": list(result.timestamps),
                "timing_type": "asr_character_token_timestamps",
            }
        except (ValueError, OSError, RuntimeError, json.JSONDecodeError):
            response = {
                "id": request_id,
                "ok": False,
                "error": "ASR request failed",
            }

        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
