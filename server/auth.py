"""
auth.py — Password hashing and JWT token logic.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
TOKEN_EXPIRE_HOURS = settings.token_expire_hours

_bearer = HTTPBearer()


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*.  Never store the original password."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored bcrypt *hashed* value."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(username: str) -> str:
    """Create a signed JWT containing *username* as the subject claim."""
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    """
    Decode *token* and return the username claim, or None if invalid/expired.
    Never raises — callers decide how to handle a missing username.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """
    FastAPI dependency: validate the Bearer token and return the username.
    Raises HTTP 401 if the token is missing, invalid, or expired.
    HTTPBearer raises HTTP 403 automatically when the header is absent entirely,
    which satisfies the spec (unauthenticated → 403, bad token → 401).
    """
    username = decode_token(credentials.credentials)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return username
