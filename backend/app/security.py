"""Security helpers: password hashing (bcrypt) and JWT access tokens."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from .config import settings


# --- Passwords ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# --- JWT access tokens ---
def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=expires_minutes or settings.access_token_expire_minutes)
    payload = {"sub": str(subject), "iat": now, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode/verify a JWT. Raises jwt.PyJWTError on any problem (expired, bad sig)."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
