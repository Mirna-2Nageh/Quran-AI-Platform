"""Safely create the first Quran AI platform administrator."""

import asyncio
import getpass
import os
import sys
from datetime import datetime, timezone
from urllib.parse import quote

sys.path.insert(0, "/app/backend")

from app.config import get_settings
from app.security.passwords import hash_password
from pydantic import EmailStr, TypeAdapter
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError


async def main():
    settings = get_settings()

    mongo_uri = settings.mongo_uri

    if not mongo_uri:
        password = os.environ.get("MONGO_APP_PASSWORD")
        if not password:
            raise SystemExit("ERROR: MongoDB credentials are unavailable.")

        mongo_uri = (
            "mongodb://quran_app:"
            + quote(password, safe="")
            + f"@mongo:27017/{settings.mongo_db_name}"
            + f"?authSource={settings.mongo_db_name}"
        )

    email = input("Admin email: ").strip().lower()
    full_name = input("Admin full name: ").strip()

    try:
        TypeAdapter(EmailStr).validate_python(email)
    except Exception:
        raise SystemExit("ERROR: Invalid email address.")

    if not 2 <= len(full_name) <= 100:
        raise SystemExit("ERROR: Name must be 2-100 characters.")

    password = getpass.getpass("Admin password (hidden): ")
    confirmation = getpass.getpass("Confirm password (hidden): ")

    if password != confirmation:
        raise SystemExit("ERROR: Passwords do not match.")

    if not 12 <= len(password) <= 128:
        raise SystemExit("ERROR: Password must be 12-128 characters.")

    if password.strip() != password:
        raise SystemExit("ERROR: Password cannot start or end with spaces.")

    client = AsyncMongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
    )

    try:
        await client.admin.command("ping")
        users = client[settings.mongo_db_name]["users"]

        existing = await users.find_one({"email": email})

        if existing:
            if existing.get("role") == "admin":
                print("Admin account already exists. No changes made.")
                return

            print(
                f"STOPPED: Email already belongs to role "
                f"'{existing.get('role')}'. No changes made."
            )
            return

        now = datetime.now(timezone.utc)

        document = {
            "email": email,
            "full_name": full_name,
            "password_hash": hash_password(password),
            "role": "admin",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }

        try:
            await users.insert_one(document)
        except DuplicateKeyError:
            print("STOPPED: Email was registered concurrently.")
            return

        print("\nAdmin account created successfully.")
        print("Email:", email)
        print("Role: admin")
        print("Password: securely hashed (Argon2id)")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
