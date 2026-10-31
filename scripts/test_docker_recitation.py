import json
import secrets
import urllib.error
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

BASE = "http://127.0.0.1:8080/api/v1"
AUDIO = Path("/tmp/quran-ai-e2e/fatiha_001002.ogg")

email = f"recitation-test-{secrets.token_hex(6)}@example.com"
password = "DockerTest!" + secrets.token_urlsafe(20)

cookies = CookieJar()
client = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cookies)
)


def send(method, path, body=None, content_type=None, csrf=None):
    headers = {"Accept": "application/json"}

    if content_type:
        headers["Content-Type"] = content_type

    if csrf:
        headers["X-CSRF-Token"] = csrf

    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        response = client.open(req, timeout=120)
    except urllib.error.HTTPError as exc:
        response = exc

    with response:
        raw = response.read()
        payload = json.loads(raw) if raw else {}
        return response.status, payload, response.headers


def json_request(method, path, payload=None, csrf=None):
    body = json.dumps(payload).encode() if payload is not None else None
    return send(
        method,
        path,
        body,
        "application/json" if body is not None else None,
        csrf,
    )


def multipart(fields, audio_bytes):
    boundary = "----QuranAITest" + secrets.token_hex(12)
    body = bytearray()

    for name, value in fields.items():
        body.extend(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode()
        )

    body.extend(
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="audio"; '
        'filename="fatiha_001002.ogg"\r\n'
        "Content-Type: audio/ogg\r\n\r\n".encode()
    )
    body.extend(audio_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    return bytes(body), f"multipart/form-data; boundary={boundary}"


def check(label, status, expected, payload):
    print(f"{label}: HTTP {status}")
    if status != expected:
        raise RuntimeError(
            f"{label}: expected {expected}, "
            f"received {status}: {payload}"
        )


canonical_path = Path("/tmp/quran-ai-e2e/expected_001002.txt")
assert canonical_path.is_file(), "Canonical Quran text file missing"

expected_text = canonical_path.read_text(encoding="utf-8").strip()
assert expected_text, "Canonical Quran text is empty"

assert AUDIO.is_file(), f"Audio file missing: {AUDIO}"
audio_bytes = AUDIO.read_bytes()
assert audio_bytes.startswith(b"OggS"), "Invalid OGG file"

print("===== REGISTER =====")
status, user, _ = json_request(
    "POST",
    "/auth/register",
    {
        "email": email,
        "full_name": "Recitation Integration Test",
        "password": password,
    },
)
check("Register", status, 201, user)
print("Test user:", email)

print("\n===== LOGIN =====")
status, user, headers = json_request(
    "POST",
    "/auth/login",
    {"email": email, "password": password},
)
check("Login", status, 200, user)
csrf = headers.get("X-CSRF-Token")
assert csrf, "Missing CSRF token"

print("\n===== AUDIO UPLOAD =====")
body, content_type = multipart({}, audio_bytes)
status, upload, _ = send(
    "POST", "/recitation/audio", body, content_type, csrf
)
check("Audio upload", status, 200, upload)
assert upload["stored"] is False
assert upload["analyzed"] is False

print("\n===== RECITATION ANALYSIS =====")

# Exact canonical Quran text will be read from the project's
# Quran text service in the backend container before this test.
canonical_path = Path("/tmp/quran-ai-e2e/expected_001002.txt")
assert canonical_path.is_file(), (
    "Missing canonical text file. Run the preparation command first."
)
expected_text = canonical_path.read_text().strip()

body, content_type = multipart(
    {
        "expected_text": expected_text,
        "surah_number": "1",
        "ayah_number": "2",
    },
    audio_bytes,
)

status, result, _ = send(
    "POST", "/recitation/analyze", body, content_type, csrf
)
check("Recitation analyze", status, 200, result)

session_id = result["session_id"]
print("Recognized text:", result["recognized_text"])
print("Alignment:", json.dumps(result["alignment"], ensure_ascii=False))
print("Word timings:", len(result["word_timings"]))
print("Tajweed analyzed:", result["tajweed_analyzed"])

assert result["recognized_text"].strip()
assert result["analysis_type"] == "word_level_asr_alignment"
assert result["tajweed_analyzed"] is False

print("\n===== HISTORY =====")
status, history, _ = send("GET", "/recitation/history")
check("History", status, 200, history)

matching = [
    item for item in history["items"]
    if item["id"] == session_id
]
assert matching, "Saved session not found in history"
assert matching[0]["recognized_text"] == result["recognized_text"]
print("Saved session found: YES")

print("\n===== LOGOUT =====")
status, payload, _ = send("POST", "/auth/logout", csrf=csrf)
check("Logout", status, 200, payload)

status, payload, _ = send("GET", "/recitation/history")
check("History after logout", status, 401, payload)

print("\nALL RECITATION E2E TESTS PASSED")
