from __future__ import annotations

import json
import os

from pwdlib import PasswordHash

from permit_pilot_core.firestore.store import FirestoreStore

from .auth import ClerkUserInDB, refresh_clerk_users

password_hash = PasswordHash.recommended()


def ensure_cloud_clerks(store: FirestoreStore) -> None:
    """Persist clerk accounts in Firestore. Bootstrap once from Cloud Run env when empty."""
    existing = store.list_clerks()
    if existing:
        refresh_clerk_users(_clerks_from_firestore(existing))
        return

    raw = os.environ.get("CLERK_USERS", "").strip()
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

    username = os.environ.get("CLERK_BOOTSTRAP_USERNAME", "maria").strip()
    password = os.environ.get("CLERK_BOOTSTRAP_PASSWORD", "").strip()
    full_name = os.environ.get("CLERK_BOOTSTRAP_FULL_NAME", "Maria Santos").strip()
    role = os.environ.get("CLERK_BOOTSTRAP_ROLE", "clerk").strip()
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
        username = str(row["username"])
        users[username] = ClerkUserInDB(
            username=username,
            full_name=str(row["full_name"]),
            role=str(row.get("role") or "clerk"),
            hashed_password=str(row["hashed_password"]),
        )
    return users
