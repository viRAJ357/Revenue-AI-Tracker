"""
auth.py — JWT Authentication & Password Hashing
================================================
Provides token generation, token verification, and password hashing
utilities for the RecoverAI API.

Reads the following environment variables:
  SECRET_KEY   — HS256 signing key (must be set in production)
  ACCESS_TOKEN_EXPIRE_MINUTES — token lifetime in minutes (default: 60)
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

logger = logging.getLogger("recoverai.auth")

# ---------------------------------------------------------------------------
# Config — loaded from environment (set via .env or Docker secret)
# ---------------------------------------------------------------------------
SECRET_KEY: str = os.environ.get("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_DO_NOT_USE_THIS")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

if SECRET_KEY == "CHANGE_ME_IN_PRODUCTION_DO_NOT_USE_THIS":
    logger.warning(
        "SECRET_KEY is using the default insecure value. "
        "Set the SECRET_KEY environment variable before deploying."
    )

# ---------------------------------------------------------------------------
# Password hashing — uses bcrypt directly (avoids passlib compatibility issues)
# ---------------------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )

def get_password_hash(password: str) -> str:
    """Return bcrypt hash of the given password."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

# ---------------------------------------------------------------------------
# JWT token generation
# ---------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.

    Parameters
    ----------
    data         : payload dict (should contain ``sub`` field)
    expires_delta: optional override for token lifetime
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# ---------------------------------------------------------------------------
# JWT token verification (FastAPI dependency)
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def verify_token(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI dependency that validates the Bearer JWT token.

    Raises HTTP 401 if the token is missing, expired, or invalid.
    Returns the decoded payload dict on success.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
        return payload
    except JWTError as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise credentials_exception
