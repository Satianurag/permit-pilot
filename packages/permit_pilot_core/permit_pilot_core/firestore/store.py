from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from google.cloud import firestore

from permit_pilot_core.firestore.credentials import firestore_client

from permit_pilot_core.models import (
    AuditEvent,
    Case,
    CaseStatus,
    Claim,
    CreateCaseRequest,
    DepartmentReview,
    IntakeDocument,
    Task,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _serialize_dt(value: datetime) -> str:
    return value.isoformat()


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class FirestoreStore:
    def __init__(self, project_id: str | None = None) -> None:
        self._db = firestore_client(project_id)

    def _cases(self):
        return self._db.collection("cases")

    def _tasks(self):
        return self._db.collection("tasks")

    def create_case(self, payload: CreateCaseRequest) -> Case:
        case_id = str(uuid.uuid4())
        now = _now()
        doc = {
            "address": payload.address,
            "bbl": payload.bbl,
            "bin": payload.bin,
            "work_type": payload.work_type,
            "owner": payload.owner,
            "borough": payload.borough,
            "status": CaseStatus.IN_REVIEW.value,
            "created_at": _serialize_dt(now),
            "updated_at": _serialize_dt(now),
        }
        self._cases().document(case_id).set(doc)
        return Case(id=case_id, **payload.model_dump(), status=CaseStatus.IN_REVIEW, created_at=now, updated_at=now)

    def get_case(self, case_id: str) -> Case | None:
        snap = self._cases().document(case_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        return Case(
            id=case_id,
            address=data["address"],
            bbl=data["bbl"],
            bin=data["bin"],
            work_type=data["work_type"],
            owner=data["owner"],
            borough=data.get("borough"),
            status=CaseStatus(data["status"]),
            created_at=_parse_dt(data["created_at"]),
            updated_at=_parse_dt(data["updated_at"]),
        )

    def list_cases(self, *, query: str | None = None) -> list[Case]:
        cases: list[Case] = []
        needle = query.strip().lower() if query else None
        for snap in self._cases().stream():
            data = snap.to_dict() or {}
            case = Case(
                id=snap.id,
                address=data["address"],
                bbl=data["bbl"],
                bin=data["bin"],
                work_type=data["work_type"],
                owner=data["owner"],
                borough=data.get("borough"),
                status=CaseStatus(data["status"]),
                created_at=_parse_dt(data["created_at"]),
                updated_at=_parse_dt(data["updated_at"]),
            )
            if needle:
                haystack = " ".join(
                    [
                        case.address,
                        case.bbl,
                        case.bin,
                        case.work_type,
                        case.owner,
                        case.borough or "",
                        case.status.value,
                    ]
                ).lower()
                if needle not in haystack:
                    continue
            cases.append(case)
        cases.sort(key=lambda c: c.updated_at, reverse=True)
        return cases

    def save_distribution(self, case_id: str, reviews: list[DepartmentReview]) -> None:
        batch = self._db.batch()
        col = self._cases().document(case_id).collection("distribution")
        for review in reviews:
            ref = col.document(review.department.value)
            batch.set(ref, review.model_dump(mode="json"))
        batch.commit()
        self._cases().document(case_id).update({"updated_at": _serialize_dt(_now())})

    def list_distribution(self, case_id: str) -> list[DepartmentReview]:
        reviews: list[DepartmentReview] = []
        for snap in self._cases().document(case_id).collection("distribution").stream():
            reviews.append(DepartmentReview.model_validate(snap.to_dict()))
        reviews.sort(key=lambda r: r.department.value)
        return reviews

    def create_task(self, case_id: str, title: str, task_type: str) -> Task:
        task_id = str(uuid.uuid4())
        now = _now()
        doc = {
            "case_id": case_id,
            "title": title,
            "task_type": task_type,
            "status": "open",
            "created_at": _serialize_dt(now),
        }
        self._tasks().document(task_id).set(doc)
        return Task(id=task_id, case_id=case_id, title=title, task_type=task_type, status="open", created_at=now)

    def list_tasks(self, case_id: str | None = None, *, status: str | None = "open") -> list[Task]:
        query: Any = self._tasks()
        if case_id:
            query = query.where(filter=firestore.FieldFilter("case_id", "==", case_id))
        if status:
            query = query.where(filter=firestore.FieldFilter("status", "==", status))
        tasks: list[Task] = []
        for snap in query.stream():
            data = snap.to_dict() or {}
            tasks.append(
                Task(
                    id=snap.id,
                    case_id=data["case_id"],
                    title=data["title"],
                    task_type=data["task_type"],
                    status=data["status"],
                    created_at=_parse_dt(data["created_at"]),
                )
            )
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks

    def complete_open_tasks_for_case(self, case_id: str) -> int:
        completed = 0
        for task in self.list_tasks(case_id, status="open"):
            self._tasks().document(task.id).update({"status": "completed"})
            completed += 1
        return completed

    def append_audit(self, case_id: str, actor: str, action: str, detail: str) -> AuditEvent:
        event_id = str(uuid.uuid4())
        now = _now()
        doc = {
            "case_id": case_id,
            "actor": actor,
            "action": action,
            "detail": detail,
            "at": _serialize_dt(now),
        }
        self._cases().document(case_id).collection("audit").document(event_id).set(doc)
        return AuditEvent(id=event_id, case_id=case_id, actor=actor, action=action, detail=detail, at=now)

    def list_audit(self, case_id: str) -> list[AuditEvent]:
        events: list[AuditEvent] = []
        for snap in self._cases().document(case_id).collection("audit").stream():
            data = snap.to_dict() or {}
            events.append(
                AuditEvent(
                    id=snap.id,
                    case_id=data["case_id"],
                    actor=data["actor"],
                    action=data["action"],
                    detail=data["detail"],
                    at=_parse_dt(data["at"]),
                )
            )
        events.sort(key=lambda e: e.at)
        return events

    def create_claim(self, case_id: str, message: str) -> Claim:
        claim_id = str(uuid.uuid4())
        now = _now()
        doc = {
            "case_id": case_id,
            "message": message,
            "status": "open",
            "response_message": None,
            "created_at": _serialize_dt(now),
            "responded_at": None,
        }
        self._cases().document(case_id).collection("claims").document(claim_id).set(doc)
        self._cases().document(case_id).update(
            {"status": CaseStatus.AWAITING_APPLICANT.value, "updated_at": _serialize_dt(now)}
        )
        return Claim(id=claim_id, case_id=case_id, message=message, status="open", created_at=now)

    def respond_to_claim(self, case_id: str, claim_id: str, response_message: str) -> Claim | None:
        ref = self._cases().document(case_id).collection("claims").document(claim_id)
        snap = ref.get()
        if not snap.exists:
            return None
        now = _now()
        ref.update(
            {
                "status": "resolved",
                "response_message": response_message,
                "responded_at": _serialize_dt(now),
            }
        )
        self._cases().document(case_id).update(
            {"status": CaseStatus.AWAITING_CLERK.value, "updated_at": _serialize_dt(now)}
        )
        data = ref.get().to_dict() or {}
        return Claim(
            id=claim_id,
            case_id=case_id,
            message=data["message"],
            status=data["status"],
            response_message=data.get("response_message"),
            created_at=_parse_dt(data["created_at"]),
            responded_at=_parse_dt(data["responded_at"]) if data.get("responded_at") else None,
        )

    def list_claims(self, case_id: str) -> list[Claim]:
        claims: list[Claim] = []
        for snap in self._cases().document(case_id).collection("claims").stream():
            data = snap.to_dict() or {}
            responded = data.get("responded_at")
            claims.append(
                Claim(
                    id=snap.id,
                    case_id=data["case_id"],
                    message=data["message"],
                    status=data["status"],
                    response_message=data.get("response_message"),
                    created_at=_parse_dt(data["created_at"]),
                    responded_at=_parse_dt(responded) if responded else None,
                )
            )
        return claims

    def set_case_status(self, case_id: str, status: CaseStatus) -> None:
        self._cases().document(case_id).update(
            {"status": status.value, "updated_at": _serialize_dt(_now())}
        )

    def count_cases(self) -> int:
        return sum(1 for _ in self._cases().stream())

    def _clerks(self):
        return self._db.collection("clerks")

    def list_clerks(self) -> list[dict[str, Any]]:
        return [(snap.to_dict() or {}) | {"username": snap.id} for snap in self._clerks().stream()]

    def upsert_clerk(
        self,
        *,
        username: str,
        full_name: str,
        role: str,
        hashed_password: str,
    ) -> None:
        self._clerks().document(username).set(
            {
                "full_name": full_name,
                "role": role,
                "hashed_password": hashed_password,
                "updated_at": _serialize_dt(_now()),
            }
        )

    def get_clerk(self, username: str) -> dict[str, Any] | None:
        snap = self._clerks().document(username).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        return {"username": username, **data}

    def get_intake_document(self, case_id: str) -> IntakeDocument | None:
        snap = self._cases().document(case_id).collection("intake").document("packet").get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        return IntakeDocument(
            redacted_text=data.get("redacted_text", ""),
            pii_findings=list(data.get("pii_findings") or []),
            stored_at=_parse_dt(data["stored_at"]),
        )

    def save_intake_packet(self, case_id: str, redacted_text: str, pii_findings: list[str]) -> None:
        self._cases().document(case_id).collection("intake").document("packet").set(
            {
                "redacted_text": redacted_text,
                "pii_findings": pii_findings,
                "stored_at": _serialize_dt(_now()),
            }
        )

    def save_workflow_steps(self, case_id: str, steps: list[Any]) -> None:
        batch = self._db.batch()
        col = self._cases().document(case_id).collection("workflow")
        for step in steps:
            data = step.model_dump(mode="json") if hasattr(step, "model_dump") else step
            name = data.get("department") or data.get("name") or "step"
            batch.set(col.document(str(name)), data)
        batch.commit()

    def list_workflow_steps(self, case_id: str) -> list[Any]:
        from permit_pilot_core.workflow.runner import WorkflowStep, WORKFLOW_DEPARTMENTS

        steps: list[WorkflowStep] = []
        for snap in self._cases().document(case_id).collection("workflow").stream():
            steps.append(WorkflowStep.model_validate(snap.to_dict()))
        order = {dept.value: i for i, dept in enumerate(WORKFLOW_DEPARTMENTS)}
        steps.sort(key=lambda s: order.get(s.department.value if s.department else s.name, 99))
        return steps

    def append_trace_span(self, span: Any) -> None:
        from permit_pilot_core.observability.traces import TraceSpan

        data = span.model_dump(mode="json") if isinstance(span, TraceSpan) else span
        span_id = data["id"]
        self._cases().document(data["case_id"]).collection("traces").document(span_id).set(data)

    def list_trace_spans(self, case_id: str) -> list[Any]:
        from permit_pilot_core.observability.traces import TraceSpan

        spans: list[TraceSpan] = []
        for snap in self._cases().document(case_id).collection("traces").stream():
            spans.append(TraceSpan.model_validate(snap.to_dict()))
        spans.sort(key=lambda s: s.started_at)
        return spans
