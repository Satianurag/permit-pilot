from __future__ import annotations

import json

from pwdlib import PasswordHash

from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.settings import get_settings

from .auth import ClerkUserInDB, refresh_clerk_users

password_hash = PasswordHash.recommended()


GOOGLE_OAUTH_SENTINEL = "oauth:google"

_store: FirestoreStore | None = None


def bind_store(store: FirestoreStore) -> None:
    global _store
    _store = store


def ensure_cloud_clerks(store: FirestoreStore) -> None:
    """Persist clerk accounts in Firestore. Bootstrap once from Cloud Run env when empty."""
    bind_store(store)
    existing = store.list_clerks()
    if existing:
        refresh_clerk_users(_clerks_from_firestore(existing))
        return

    settings = get_settings()
    raw = settings.clerk_users_json.strip()
    if raw:
        users: dict[str, ClerkUserInDB] = {}
        for row in json.loads(raw):
            user = ClerkUserInDB.model_validate(row)
            store.upsert_clerk(
                username=user.username,
                full_name=user.full_name,
                role=user.role,
                hashed_password=user.hashed_password,
            )
            users[user.username] = user
        refresh_clerk_users(users)
        return

    username = settings.clerk_bootstrap_username.strip()
    password = settings.clerk_bootstrap_password.strip()
    full_name = settings.clerk_bootstrap_full_name.strip()
    role = settings.clerk_bootstrap_role.strip() or "clerk"
    if not password:
        raise RuntimeError("Set CLERK_BOOTSTRAP_PASSWORD or CLERK_USERS on Cloud Run")

    hashed = password_hash.hash(password)
    store.upsert_clerk(
        username=username,
        full_name=full_name,
        role=role,
        hashed_password=hashed,
    )
    refresh_clerk_users(
        {
            username: ClerkUserInDB(
                username=username,
                full_name=full_name,
                role=role,
                hashed_password=hashed,
            )
        }
    )


def _clerks_from_firestore(rows: list[dict[str, object]]) -> dict[str, ClerkUserInDB]:
    users: dict[str, ClerkUserInDB] = {}
    for row in rows:
        username = str(row.get("username") or "")
        if not username:
            continue
        hashed = str(row.get("hashed_password") or GOOGLE_OAUTH_SENTINEL)
        users[username] = ClerkUserInDB(
            username=username,
            full_name=str(row.get("full_name") or username),
            role=str(row.get("role") or "clerk"),
            hashed_password=hashed,
        )
    return users


def load_clerk(username: str) -> ClerkUserInDB | None:
    if _store is None:
        return None
    row = _store.get_clerk(username)
    if not row:
        return None
    users = _clerks_from_firestore([row])
    user = users.get(username)
    if user:
        from .auth import clerk_users_or_empty

        current = dict(clerk_users_or_empty())
        current[username] = user
        refresh_clerk_users(current)
    return user


def upsert_google_clerk(*, email: str, full_name: str) -> ClerkUserInDB:
    if _store is None:
        raise RuntimeError("Clerk store is not bound")
    existing = _store.get_clerk(email)
    hashed = GOOGLE_OAUTH_SENTINEL
    role = "clerk"
    if existing:
        prior = str(existing.get("hashed_password") or "")
        if prior and not prior.startswith("oauth:"):
            hashed = prior
        role = str(existing.get("role") or "clerk")
        full_name = full_name or str(existing.get("full_name") or email)
    _store.upsert_clerk(username=email, full_name=full_name or email, role=role, hashed_password=hashed)
    user = ClerkUserInDB(username=email, full_name=full_name or email, role=role, hashed_password=hashed)
    from .auth import clerk_users_or_empty

    current = dict(clerk_users_or_empty())
    current[email] = user
    refresh_clerk_users(current)
    return user
