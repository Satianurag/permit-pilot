from __future__ import annotations

import json

from pwdlib import PasswordHash

from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.settings import get_settings

from .auth import ClerkUserInDB, refresh_clerk_users

password_hash = PasswordHash.recommended()


def ensure_cloud_clerks(store: FirestoreStore) -> None:
    """Persist clerk accounts in Firestore. Bootstrap once from Cloud Run env when empty."""
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
        hashed = str(row.get("hashed_password") or "")
        if not username or not hashed:
            continue
        users[username] = ClerkUserInDB(
            username=username,
            full_name=str(row.get("full_name") or username),
            role=str(row.get("role") or "clerk"),
            hashed_password=hashed,
        )
    return users
