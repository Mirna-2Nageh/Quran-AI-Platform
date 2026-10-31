#!/bin/sh
set -eu

export QURAN_AI_MONGO_URI="$(
  python - <<'PY'
import os
from urllib.parse import quote

password = os.environ["MONGO_APP_PASSWORD"]

print(
    "mongodb://quran_app:"
    + quote(password, safe="")
    + "@mongo:27017/quran_ai?authSource=quran_ai"
)
PY
)"

exec uvicorn app.main:app \
  --app-dir /app/backend \
  --host 0.0.0.0 \
  --port 8000
