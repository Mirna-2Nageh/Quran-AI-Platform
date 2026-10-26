# Current Implementation — October 2026

## Implemented Components

- React, TypeScript, and Vite frontend.
- FastAPI backend with MongoDB persistence.
- User authentication and protected endpoints.
- Quran reader and recitation practice interfaces.
- Audio recording and upload.
- Quran ASR using sherpa-onnx.
- Word-level recitation alignment.
- User-specific recitation history.

Word-level alignment is not Tajweed evaluation.

## Local Development

- Backend: http://localhost:8001
- Frontend: http://localhost:5173
- MongoDB: 127.0.0.1:27018

Start MongoDB:

    docker compose --env-file .env.mongo up -d mongo

The .env.mongo file must define MONGO_ROOT_PASSWORD.
Never commit local credentials.

## ASR Requirements

- FFmpeg
- Python virtual environment: .venv-asr
- sherpa-onnx
- numpy
- scipy
- soundfile

The model is based on Abdou/quran-asr-small.
Reference revision: 5d36fbd7934f9d9a10ab0cc67df07065e35f6871

The model.int8.onnx weights are excluded from Git.

Expected local model SHA-256:
88f9df290d57b8890275d79187b77515aeeb12626a42bc76cbd0f8bfcaff00f0

Local audio benchmark recordings are also excluded from Git.

## ASR Setup

Create the isolated ASR environment:

    python3 -m venv .venv-asr
    .venv-asr/bin/python -m pip install sherpa-onnx soundfile numpy scipy

Download the compatible model.int8.onnx from the referenced
Hugging Face model revision and place it at:

    models/quran-asr-small/model.int8.onnx

Verify the downloaded model:

    sha256sum models/quran-asr-small/model.int8.onnx

Run transcription on a local WAV recording:

    .venv-asr/bin/python models/quran-asr-small/transcribe.py path/to/recitation.wav --standard

## Tests

Backend tests (with backend dependencies installed):

    .venv/bin/python -m pytest backend/tests -q

ASR evaluation unit tests:

    .venv/bin/python -m pytest tests/asr_evaluation/test_evaluation.py -q

The full ASR benchmark requires the recordings referenced in
tests/asr_evaluation/manifest.json. These recordings are not
included in Git.

The small Al-Fatiha benchmark does not establish general
accuracy across speakers, recording conditions, or narrations.
