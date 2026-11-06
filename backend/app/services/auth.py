from datetime import datetime, timedelta, timezone

from app.config import get_settings
from app.repositories.users import (
    UserRepository,
)
from app.security.passwords import hash_password, verify_password
from app.security.rate_limit import LoginRateLimiter
from app.security.sessions import (
    generate_csrf_token,
    derive_csrf_token,
    generate_session_token,
    hash_session_token,
)


class InvalidCredentialsError(Exception):
    pass


class TooManyLoginAttemptsError(Exception):
    pass


class AuthService:
    def __init__(self, database):
        self.database = database
        self.csrf_secret = get_settings().csrf_secret
        self.users = UserRepository(database)
        self.sessions = database["sessions"]
        self.rate_limiter = LoginRateLimiter(database)

    async def register(self, email, full_name, password):
        normalized_email = email.strip().lower()

        return await self.users.create(
            email=normalized_email,
            full_name=full_name.strip(),
            password_hash=hash_password(password),
        )

    async def login(self, email, password):
        normalized_email = email.strip().lower()

        if await self.rate_limiter.is_blocked(normalized_email):
            raise TooManyLoginAttemptsError()

        user = await self.users.get_by_email(normalized_email)

        if (
            user is None
            or not user.get("is_active", False)
            or not verify_password(
                password,
                user["password_hash"],
            )
        ):
            await self.rate_limiter.record_failure(normalized_email)
            raise InvalidCredentialsError()

        await self.rate_limiter.clear(normalized_email)

        token = generate_session_token()
        csrf_token = derive_csrf_token(token, self._csrf_secret())

        await self.sessions.insert_one(
            {
                "token_hash": hash_session_token(token),
                "csrf_version": 2,
                "user_id": user["_id"],
                "created_at": datetime.now(timezone.utc),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)),
            }
        )

        return user, token, csrf_token

    async def get_current_user(self, token):
        if not token:
            return None

        session = await self.sessions.find_one(
            {
                "token_hash": hash_session_token(token),
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            }
        )

        if session is None:
            return None

        user = await self.users.get_by_id(session["user_id"])

        if user is None or not user.get("is_active", False):
            return None

        return user

    def _csrf_secret(self):
        if not self.csrf_secret or len(self.csrf_secret) < 64:
            raise RuntimeError("Strong CSRF secret is required")
        return self.csrf_secret

    async def refresh_csrf(self, session_token):
        if not session_token:
            return None

        session = await self.sessions.find_one({
            "token_hash": hash_session_token(session_token),
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        })
        if session is None:
            return None

        return derive_csrf_token(session_token, self._csrf_secret())

    async def verify_csrf(self, session_token, csrf_token):
        if not session_token or not csrf_token:
            return False

        session = await self.sessions.find_one({
            "token_hash": hash_session_token(session_token),
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        })
        if session is None:
            return False

        import hmac

        expected = derive_csrf_token(session_token, self._csrf_secret())
        if hmac.compare_digest(expected, csrf_token):
            return True

        if session.get("csrf_version") == 2:
            return False

        legacy_hash = session.get("csrf_hash")
        return bool(
            legacy_hash
            and hmac.compare_digest(
                legacy_hash,
                hash_session_token(csrf_token),
            )
        )

    async def logout(self, token):
        if token:
            await self.sessions.delete_one({"token_hash": hash_session_token(token)})
