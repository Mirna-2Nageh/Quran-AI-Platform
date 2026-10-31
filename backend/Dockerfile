FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       libsndfile1 \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml
COPY backend /app/backend

RUN python -m pip install --upgrade pip \
    && python -m pip install .

# Isolated ASR environment expected by quran_asr.py
RUN python -m venv /app/.venv-asr \
    && /app/.venv-asr/bin/pip install \
       sherpa-onnx \
       soundfile \
       numpy \
       scipy

COPY models/quran-asr-small /app/models/quran-asr-small

WORKDIR /app

EXPOSE 8000

CMD ["sh", "/app/backend/docker/start.sh"]
