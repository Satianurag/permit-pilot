from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from permit_pilot_core.settings import get_settings


def public_base_url() -> str:
    """Cloud Run URL used as Cloud Tasks OIDC audience.

    Older deploys concatenated PERMIT_PILOT_URL and CORS_ORIGINS with ``@``.
    """
    settings = get_settings()
    raw = (settings.permit_pilot_url or "").split("@", 1)[0].strip().rstrip("/")
    if not raw:
        raise RuntimeError("PERMIT_PILOT_URL is required to enqueue Cloud Tasks")
    return raw


def case_id_from_firestore_name(name: str) -> str | None:
    """Extract case id from a Firestore document resource name."""
    if "/documents/" not in name:
        return None
    path = name.split("/documents/", 1)[1]
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "cases":
        return parts[1]
    return None


def case_id_from_eventarc_payload(body: dict[str, Any]) -> str | None:
    if body.get("case_id"):
        return str(body["case_id"])
    message = body.get("message") if isinstance(body.get("message"), dict) else None
    if message:
        attrs = message.get("attributes") or {}
        if isinstance(attrs, dict):
            for key in ("ce-document", "ce-subject", "document"):
                found = case_id_from_firestore_name(str(attrs.get(key) or ""))
                if found:
                    return found
                raw = str(attrs.get(key) or "")
                if "cases/" in raw:
                    part = raw.split("cases/", 1)[-1].split("/")[0]
                    if part:
                        return part
    data = body.get("data") if isinstance(body.get("data"), dict) else body
    for key in ("value", "oldValue"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, dict):
            found = case_id_from_firestore_name(str(value.get("name") or ""))
            if found:
                return found
    proto = data.get("value") if isinstance(data, dict) else None
    if isinstance(proto, dict):
        found = case_id_from_firestore_name(str(proto.get("name") or ""))
        if found:
            return found
    return case_id_from_firestore_name(str(body.get("document") or body.get("name") or ""))


def claim_status_from_eventarc_payload(body: dict[str, Any]) -> str:
    data = body.get("data") if isinstance(body.get("data"), dict) else body
    value = data.get("value") if isinstance(data, dict) else None
    if not isinstance(value, dict):
        return ""
    fields = value.get("fields") or {}
    status = fields.get("status") or {}
    if isinstance(status, dict):
        return str(status.get("stringValue") or "")
    return str(status or "")


def enqueue_distribution(
    *,
    case_id: str,
    reason: str = "intake",
    delay_seconds: int = 0,
) -> str:
    settings = get_settings()
    base = public_base_url()
    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(
        settings.project_id, settings.cloud_tasks_location, settings.cloud_tasks_queue
    )
    url = f"{base}/api/internal/distribution/run"
    sa = (
        settings.cloud_tasks_service_account
        or f"permit-pilot-tasks@{settings.project_id}.iam.gserviceaccount.com"
    )
    http_request = {
        "http_method": tasks_v2.HttpMethod.POST,
        "url": url,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"case_id": case_id, "reason": reason}).encode(),
        "oidc_token": {
            "service_account_email": sa,
            "audience": base,
        },
    }
    task: dict[str, Any] = {"http_request": http_request}
    if delay_seconds > 0:
        when = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        stamp = timestamp_pb2.Timestamp()
        stamp.FromDatetime(when)
        task["schedule_time"] = stamp
    created = client.create_task(request={"parent": parent, "task": task})
    return created.name
