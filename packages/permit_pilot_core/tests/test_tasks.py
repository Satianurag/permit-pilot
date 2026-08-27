"""Cloud Tasks payload helpers for Eventarc Firestore resumes."""

from __future__ import annotations

import unittest

from permit_pilot_core.platform.tasks import (
    case_id_from_eventarc_payload,
    case_id_from_firestore_name,
    claim_status_from_eventarc_payload,
)


class TasksParseTest(unittest.TestCase):
    def test_firestore_name(self) -> None:
        name = (
            "projects/gen-lang-client-0233250350/databases/(default)/documents/"
            "cases/abc-123/claims/claim-9"
        )
        self.assertEqual(case_id_from_firestore_name(name), "abc-123")

    def test_eventarc_cloudevent(self) -> None:
        body = {
            "specversion": "1.0",
            "type": "google.cloud.firestore.document.v1.written",
            "data": {
                "value": {
                    "name": "projects/p/databases/(default)/documents/cases/case-42/claims/c1",
                    "fields": {"status": {"stringValue": "resolved"}},
                }
            },
        }
        self.assertEqual(case_id_from_eventarc_payload(body), "case-42")
        self.assertEqual(claim_status_from_eventarc_payload(body), "resolved")

    def test_pubsub_envelope_attributes(self) -> None:
        body = {
            "message": {
                "attributes": {
                    "ce-document": "cases/case-99/claims/c2",
                    "ce-type": "google.cloud.firestore.document.v1.updated",
                }
            }
        }
        self.assertEqual(case_id_from_eventarc_payload(body), "case-99")

    def test_open_claim_is_not_resume(self) -> None:
        body = {
            "data": {
                "value": {
                    "name": "projects/p/databases/(default)/documents/cases/case-42/claims/c1",
                    "fields": {"status": {"stringValue": "open"}},
                }
            }
        }
        self.assertEqual(claim_status_from_eventarc_payload(body), "open")
