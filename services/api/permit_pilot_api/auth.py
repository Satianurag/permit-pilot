from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
password_hash = PasswordHash.recommended()
_dummy_hash = password_hash.hash("permit-pilot-auth-timing-mitigation")

_USERS: dict[str, "ClerkUserInDB"] = {}


class ClerkUser(BaseModel):
    username: str
    full_name: str
    role: str = "clerk"


class ClerkUserInDB(ClerkUser):
    hashed_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


def refresh_clerk_users(users: dict[str, ClerkUserInDB]) -> None:
    global _USERS
    _USERS = users


def _secret_key() -> str:
    key = os.environ.get("AUTH_SECRET_KEY", "").strip()
    if not key:
        raise RuntimeError("AUTH_SECRET_KEY must be set on Cloud Run")
    return key


def clerk_users() -> dict[str, ClerkUserInDB]:
    if not _USERS:
        raise RuntimeError("Clerk accounts are not loaded yet")
    return _USERS


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str) -> ClerkUserInDB | None:
    users = clerk_users()
    user = users.get(username)
    if not user:
        verify_password(password, _dummy_hash)
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(*, username: str, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "role": role, "exp": expire}
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> ClerkUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str):
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception from None

    user = clerk_users().get(username)
    if user is None:
        raise credentials_exception
    return ClerkUser(username=user.username, full_name=user.full_name, role=user.role)


async def get_current_admin(current_user: Annotated[ClerkUser, Depends(get_current_user)]) -> ClerkUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def clerk_actor(user: ClerkUser) -> str:
    return f"{user.full_name} ({user.username})"
