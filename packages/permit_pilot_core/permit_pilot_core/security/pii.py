from __future__ import annotations

import os
import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
    (re.compile(r"\b\d{9}\b"), "[REDACTED-SSN]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED-EMAIL]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[REDACTED-PHONE]"),
]

_DLP_INFO_TYPES = [
    {"name": "EMAIL_ADDRESS"},
    {"name": "PHONE_NUMBER"},
    {"name": "US_SOCIAL_SECURITY_NUMBER"},
    {"name": "PERSON_NAME"},
]


def _redact_regex(text: str) -> tuple[str, list[str]]:
    redacted = text
    findings: list[str] = []
    for pattern, replacement in _PATTERNS:
        matches = pattern.findall(redacted)
        if matches:
            findings.append(f"{replacement}: {len(matches)} occurrence(s)")
            redacted = pattern.sub(replacement, redacted)
    return redacted, findings


def _redact_dlp(text: str, project_id: str) -> tuple[str, list[str]]:
    from google.cloud import dlp_v2

    client = dlp_v2.DlpServiceClient()
    parent = f"projects/{project_id}/locations/global"
    response = client.deidentify_content(
        request={
            "parent": parent,
            "item": {"value": text},
            "inspect_config": {"info_types": _DLP_INFO_TYPES},
            "deidentify_config": {
                "info_type_transformations": {
                    "transformations": [
                        {
                            "primitive_transformation": {
                                "replace_with_info_type_config": {},
                            }
                        }
                    ]
                }
            },
        }
    )
    redacted = response.item.value
    findings: list[str] = ["Google Cloud DLP de-identification applied"]
    if response.overview and response.overview.transformed_bytes:
        findings.append(f"bytes_transformed={response.overview.transformed_bytes}")
    return redacted, findings


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Redact PII with Cloud DLP on Cloud Run; regex fallback for local development."""
    if not text.strip():
        return text, []
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project and os.environ.get("K_SERVICE"):
        return _redact_dlp(text, project)
    redacted, findings = _redact_regex(text)
    if findings:
        findings.insert(0, "Local regex redaction (Cloud DLP used in production)")
    return redacted, findings
