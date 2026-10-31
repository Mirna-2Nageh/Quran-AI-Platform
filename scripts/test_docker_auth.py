import json
import secrets
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

BASE_URL = "http://127.0.0.1:8080/api/v1/auth"

email = f"docker-test-{secrets.token_hex(6)}@example.com"
password = "DockerTest!" + secrets.token_urlsafe(20)

cookies = CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(cookies)
)


def request(method, path, data=None, csrf=None):
    headers = {"Accept": "application/json"}

    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()

    if csrf:
        headers["X-CSRF-Token"] = csrf

    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with opener.open(req, timeout=15) as response:
            body = response.read().decode()
            return (
                response.status,
                json.loads(body) if body else {},
                response.headers,
            )
    except urllib.error.HTTPError as error:
        body = error.read().decode()
        return (
            error.code,
            json.loads(body) if body else {},
            error.headers,
        )


def check(label, actual, expected):
    print(f"{label}: HTTP {actual}")
    if actual != expected:
        raise RuntimeError(
            f"{label} failed: expected {expected}, got {actual}"
        )


print("===== REGISTER =====")
status, user, _ = request(
    "POST",
    "/register",
    {
        "email": email,
        "full_name": "Docker Integration Test",
        "password": password,
    },
)
check("Register", status, 201)
print("Test user created:", email)


print("\n===== LOGIN =====")
status, user, headers = request(
    "POST",
    "/login",
    {"email": email, "password": password},
)
check("Login", status, 200)

csrf_token = headers.get("X-CSRF-Token")
assert csrf_token, "Login did not return CSRF token"
assert any(c.name == "quran_session" for c in cookies)
print("Session cookie: OK")
print("CSRF token: OK")


print("\n===== CURRENT USER =====")
status, current_user, _ = request("GET", "/me")
check("Current user", status, 200)
assert current_user["email"] == email


print("\n===== CSRF REFRESH =====")
status, _, headers = request("GET", "/csrf")
check("CSRF refresh", status, 200)
csrf_token = headers.get("X-CSRF-Token")
assert csrf_token, "CSRF refresh did not return token"


print("\n===== LOGOUT =====")
status, _, _ = request("POST", "/logout", csrf=csrf_token)
check("Logout", status, 200)


print("\n===== SESSION REVOCATION =====")
status, _, _ = request("GET", "/me")
check("Session revoked", status, 401)


print("\nALL AUTH INTEGRATION TESTS PASSED")
