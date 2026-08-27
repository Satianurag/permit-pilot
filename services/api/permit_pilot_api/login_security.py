"""Track failed sign-in attempts in Firestore for audit logging and rate limiting."""

from __future__ import annotations

import logging
import time

from google.cloud import firestore

from permit_pilot_core.settings import get_settings

_log = logging.getLogger("permit_pilot.auth")


def _db() -> firestore.Client:
    return firestore.Client(project=get_settings().project_id)


def _doc_ref(username: str) -> firestore.DocumentReference:
    user = username.strip().lower()
    return _db().collection("login_security").document(user)


def _recent_timestamps(raw: list[float] | None) -> list[float]:
    now = time.time()
    window = get_settings().login_window_seconds
    return [t for t in (raw or []) if now - t < window]


def record_failed_login(username: str) -> None:
    user = username.strip().lower()
    if not user:
        return
    ref = _doc_ref(user)
    snap = ref.get()
    recent = _recent_timestamps(snap.to_dict().get("timestamps") if snap.exists else None)
    recent.append(time.time())
    ref.set({"timestamps": recent})
    _log.warning(
        "Failed sign-in attempt username=%s failures_in_window=%d",
        user,
        len(recent),
    )


def is_login_locked(username: str) -> bool:
    user = username.strip().lower()
    if not user:
        return False
    snap = _doc_ref(user).get()
    if not snap.exists:
        return False
    recent = _recent_timestamps(snap.to_dict().get("timestamps"))
    return len(recent) >= get_settings().login_max_failures


def clear_failures(username: str) -> None:
    user = username.strip().lower()
    if user:
        _doc_ref(user).delete()
