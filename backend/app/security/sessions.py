import hashlib
import secrets


def generate_session_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Store only a SHA-256 digest of the session token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    """Generate a random CSRF token for an authenticated session."""
    return secrets.token_urlsafe(32)


def derive_csrf_token(session_token: str, secret: str) -> str:
    """Derive a stable, session-bound CSRF token using HMAC-SHA256."""
    import hmac

    if not session_token or not secret:
        raise ValueError("Session token and CSRF secret are required")

    digest = hmac.new(
        secret.encode("utf-8"),
        ("quran-ai:csrf:v1:" + session_token).encode("utf-8"),
        hashlib.sha256,
    )
    return digest.hexdigest()
