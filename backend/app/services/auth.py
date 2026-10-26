from datetime import datetime, timedelta, timezone

from app.repositories.users import (
    UserRepository,
)
from app.security.passwords import hash_password, verify_password
from app.security.sessions import (
    generate_session_token,
    hash_session_token,
)


class InvalidCredentialsError(Exception):
    pass


class AuthService:
    def __init__(self, database):
        self.database = database
        self.users = UserRepository(database)
        self.sessions = database["sessions"]

    async def register(self, email, full_name, password):
        normalized_email = email.strip().lower()

        return await self.users.create(
            email=normalized_email,
            full_name=full_name.strip(),
            password_hash=hash_password(password),
        )

    async def login(self, email, password):
        user = await self.users.get_by_email(email.strip().lower())

        if (
            user is None
            or not user.get("is_active", False)
            or not verify_password(
                password,
                user["password_hash"],
            )
        ):
            raise InvalidCredentialsError()

        token = generate_session_token()

        await self.sessions.insert_one(
            {
                "token_hash": hash_session_token(token),
                "user_id": user["_id"],
                "created_at": datetime.now(timezone.utc),
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)),
            }
        )

        return user, token

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

    async def logout(self, token):
        if token:
            await self.sessions.delete_one({"token_hash": hash_session_token(token)})
