from app.security.passwords import hash_password, verify_password
from app.security.sessions import (
    generate_session_token,
    hash_session_token,
)


def test_password_hashing() -> None:
    password = "SecurePassword123!"

    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash.startswith("$argon2id$")
    assert verify_password(password, password_hash)


def test_invalid_password() -> None:
    password_hash = hash_password("CorrectPassword123!")

    assert not verify_password(
        "WrongPassword123!",
        password_hash,
    )


def test_invalid_hash() -> None:
    assert not verify_password(
        "SomePassword123!",
        "invalid-hash",
    )


def test_session_tokens_are_unique() -> None:
    first = generate_session_token()
    second = generate_session_token()

    assert first != second


def test_session_hash_is_deterministic() -> None:
    token = generate_session_token()

    assert hash_session_token(token) == hash_session_token(token)
    assert hash_session_token(token) != token
