from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from google.cloud import firestore

from permit_pilot_core.firestore.credentials import firestore_client

from permit_pilot_core.models import (
    AuditEvent,
    Case,
    CaseStatus,
    Claim,
    CreateCaseRequest,
    DashboardActivity,
    DashboardAlert,
    DashboardDepartmentRollup,
    DashboardSummary,
    DepartmentReview,
    IntakeDocument,
    ReviewStatus,
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

    def update_case(self, case_id: str, fields: dict[str, Any]) -> Case | None:
        ref = self._cases().document(case_id)
        if not ref.get().exists:
            return None
        allowed = {"address", "bbl", "bin", "work_type", "owner", "borough"}
        updates: dict[str, Any] = {}
        for key, value in fields.items():
            if key in allowed and value is not None and str(value).strip():
                updates[key] = str(value).strip()
        if not updates:
            return self.get_case(case_id)
        updates["updated_at"] = _serialize_dt(_now())
        ref.update(updates)
        return self.get_case(case_id)

    def list_cases(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Case]:
        cases: list[Case] = []
        needle = query.strip().lower() if query else None
        status_needle = status.strip().lower() if status else None
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
            if status_needle and case.status.value != status_needle:
                continue
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
        if offset:
            cases = cases[offset:]
        if limit > 0:
            cases = cases[:limit]
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

    def create_task(
        self,
        case_id: str,
        title: str,
        task_type: str,
        *,
        assignee: str | None = None,
    ) -> Task:
        task_id = str(uuid.uuid4())
        now = _now()
        doc = {
            "case_id": case_id,
            "title": title,
            "task_type": task_type,
            "status": "open",
            "assignee": assignee,
            "created_at": _serialize_dt(now),
        }
        self._tasks().document(task_id).set(doc)
        return Task(
            id=task_id,
            case_id=case_id,
            title=title,
            task_type=task_type,
            status="open",
            assignee=assignee,
            created_at=now,
        )

    def get_task(self, task_id: str) -> Task | None:
        snap = self._tasks().document(task_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        return Task(
            id=snap.id,
            case_id=data["case_id"],
            title=data["title"],
            task_type=data["task_type"],
            status=data["status"],
            assignee=data.get("assignee"),
            created_at=_parse_dt(data["created_at"]),
        )

    def assign_task(self, task_id: str, assignee: str) -> Task | None:
        ref = self._tasks().document(task_id)
        if not ref.get().exists:
            return None
        ref.update({"assignee": assignee})
        return self.get_task(task_id)

    def list_tasks(
        self,
        case_id: str | None = None,
        *,
        status: str | None = "open",
        assignee: str | None = None,
        unassigned_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Task]:
        query: Any = self._tasks()
        if case_id:
            query = query.where(filter=firestore.FieldFilter("case_id", "==", case_id))
        if status:
            query = query.where(filter=firestore.FieldFilter("status", "==", status))
        if assignee and not unassigned_only:
            query = query.where(filter=firestore.FieldFilter("assignee", "==", assignee))
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
                    assignee=data.get("assignee"),
                    created_at=_parse_dt(data["created_at"]),
                )
            )
        if unassigned_only:
            tasks = [task for task in tasks if not task.assignee]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        if offset:
            tasks = tasks[offset:]
        if limit > 0:
            tasks = tasks[:limit]
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

    def create_claim(self, case_id: str, message: str, *, notify: bool = True) -> Claim:
        claim_id = str(uuid.uuid4())
        now = _now()
        notification_reference = f"DOB-NOW-{case_id[:8].upper()}-{claim_id[:6].upper()}"
        doc = {
            "case_id": case_id,
            "message": message,
            "status": "open",
            "response_message": None,
            "notification_channel": "dob_now_manual" if notify else None,
            "notification_reference": notification_reference if notify else None,
            "notified_at": None,
            "manual_dob_now_sent": False,
            "created_at": _serialize_dt(now),
            "responded_at": None,
        }
        self._cases().document(case_id).collection("claims").document(claim_id).set(doc)
        self._cases().document(case_id).update(
            {"status": CaseStatus.AWAITING_APPLICANT.value, "updated_at": _serialize_dt(now)}
        )
        return Claim(
            id=claim_id,
            case_id=case_id,
            message=message,
            status="open",
            notification_channel=doc["notification_channel"],
            notification_reference=doc["notification_reference"],
            notified_at=None,
            manual_dob_now_sent=False,
            created_at=now,
        )

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
            notification_channel=data.get("notification_channel"),
            notification_reference=data.get("notification_reference"),
            notified_at=_parse_dt(data["notified_at"]) if data.get("notified_at") else None,
            manual_dob_now_sent=bool(data.get("manual_dob_now_sent")),
            created_at=_parse_dt(data["created_at"]),
            responded_at=_parse_dt(data["responded_at"]) if data.get("responded_at") else None,
        )

    def mark_claim_dob_now_sent(self, case_id: str, claim_id: str) -> Claim | None:
        ref = self._cases().document(case_id).collection("claims").document(claim_id)
        snap = ref.get()
        if not snap.exists:
            return None
        now = _now()
        ref.update({"manual_dob_now_sent": True, "notified_at": _serialize_dt(now)})
        data = ref.get().to_dict() or {}
        return Claim(
            id=claim_id,
            case_id=case_id,
            message=data["message"],
            status=data["status"],
            response_message=data.get("response_message"),
            notification_channel=data.get("notification_channel"),
            notification_reference=data.get("notification_reference"),
            notified_at=_parse_dt(data["notified_at"]) if data.get("notified_at") else None,
            manual_dob_now_sent=bool(data.get("manual_dob_now_sent")),
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
                    notification_channel=data.get("notification_channel"),
                    notification_reference=data.get("notification_reference"),
                    notified_at=_parse_dt(data["notified_at"]) if data.get("notified_at") else None,
                    manual_dob_now_sent=bool(data.get("manual_dob_now_sent")),
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
        pdf_snap = self._cases().document(case_id).collection("intake").document("plan_pdf").get()
        has_pdf = pdf_snap.exists
        return IntakeDocument(
            redacted_text=data.get("redacted_text", ""),
            pii_findings=list(data.get("pii_findings") or []),
            stored_at=_parse_dt(data["stored_at"]),
            filename=data.get("filename"),
            content_type=data.get("content_type"),
            has_pdf=has_pdf,
        )

    def save_intake_packet(
        self,
        case_id: str,
        redacted_text: str,
        pii_findings: list[str],
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> None:
        self._cases().document(case_id).collection("intake").document("packet").set(
            {
                "redacted_text": redacted_text,
                "pii_findings": pii_findings,
                "stored_at": _serialize_dt(_now()),
                "filename": filename,
                "content_type": content_type,
            }
        )

    def save_intake_pdf(self, case_id: str, *, filename: str, content_type: str, pdf_base64: str) -> None:
        self._cases().document(case_id).collection("intake").document("plan_pdf").set(
            {
                "filename": filename,
                "content_type": content_type,
                "pdf_base64": pdf_base64,
                "stored_at": _serialize_dt(_now()),
            }
        )

    def get_intake_pdf(self, case_id: str) -> dict[str, str] | None:
        snap = self._cases().document(case_id).collection("intake").document("plan_pdf").get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        if not data.get("pdf_base64"):
            return None
        return {
            "filename": str(data.get("filename") or "plan.pdf"),
            "content_type": str(data.get("content_type") or "application/pdf"),
            "pdf_base64": str(data["pdf_base64"]),
        }

    def save_briefing(self, case_id: str, *, summary: str, model: str, generated_by: str) -> None:
        now = _now()
        self._cases().document(case_id).collection("briefing").document("latest").set(
            {
                "summary": summary,
                "model": model,
                "generated_by": generated_by,
                "generated_at": _serialize_dt(now),
            }
        )

    def get_briefing(self, case_id: str) -> dict[str, Any] | None:
        snap = self._cases().document(case_id).collection("briefing").document("latest").get()
        if not snap.exists:
            return None
        return snap.to_dict() or None

    def get_context_cache(self, case_id: str, *, ttl_seconds: int = 3600) -> dict[str, Any] | None:
        snap = self._cases().document(case_id).collection("meta").document("context_cache").get()
        if not snap.exists:
            return None
        data = snap.to_dict() or {}
        cached_at = data.get("cached_at")
        if not cached_at:
            return None
        age = (_now() - _parse_dt(cached_at)).total_seconds()
        if age > ttl_seconds:
            return None
        return {
            "related_permits": data.get("related_permits") or [],
            "parcel": data.get("parcel"),
        }

    def save_context_cache(
        self,
        case_id: str,
        *,
        related_permits: list[dict[str, Any]],
        parcel: dict[str, Any] | None,
    ) -> None:
        self._cases().document(case_id).collection("meta").document("context_cache").set(
            {
                "related_permits": related_permits,
                "parcel": parcel,
                "cached_at": _serialize_dt(_now()),
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

    def dashboard_summary(self, *, username: str, review_window_days: int = 5) -> DashboardSummary:
        now = _now()
        review_cutoff = now - timedelta(days=review_window_days)
        distribution_stale_cutoff = now - timedelta(hours=24)
        terminal = {CaseStatus.APPROVED, CaseStatus.CHANGES_REQUESTED}

        open_tasks = self.list_tasks(status="open", limit=500)
        overdue_tasks = 0
        unassigned_tasks = 0
        my_tasks = 0
        for task in open_tasks:
            if not task.assignee:
                unassigned_tasks += 1
            if task.assignee == username:
                my_tasks += 1
            if task.created_at < review_cutoff:
                overdue_tasks += 1

        all_cases = self.list_cases(limit=500)
        cases_by_status: dict[str, int] = {}
        awaiting_applicant = 0
        awaiting_clerk = 0
        in_review = 0
        case_by_id: dict[str, Case] = {}

        for case in all_cases:
            case_by_id[case.id] = case
            key = case.status.value
            cases_by_status[key] = cases_by_status.get(key, 0) + 1
            if case.status == CaseStatus.AWAITING_APPLICANT:
                awaiting_applicant += 1
            elif case.status == CaseStatus.AWAITING_CLERK:
                awaiting_clerk += 1
            elif case.status == CaseStatus.IN_REVIEW:
                in_review += 1

        dept_totals: dict[str, dict[str, int]] = {}
        stale_distribution = 0
        failed_department_reviews = 0
        interrupted_workflows = 0
        alerts: list[DashboardAlert] = []
        alert_keys: set[str] = set()

        def push_alert(kind: str, title: str, detail: str, case_id: str, tab: str = "distribution") -> None:
            key = f"{kind}:{case_id}:{title}"
            if key in alert_keys:
                return
            alert_keys.add(key)
            alerts.append(
                DashboardAlert(
                    id=str(uuid.uuid4()),
                    kind=kind,
                    title=title,
                    detail=detail,
                    case_id=case_id,
                    href=f"/cases/{case_id}?tab={tab}",
                )
            )

        for case in all_cases:
            if case.status in terminal:
                continue

            reviews = self.list_distribution(case.id)
            if reviews:
                latest = max(review.updated_at for review in reviews)
                if latest < distribution_stale_cutoff:
                    stale_distribution += 1
                    push_alert(
                        "stale_distribution",
                        f"Distribution stale — {case.address}",
                        "NYC Open Data pull is older than 24 hours.",
                        case.id,
                    )

            for review in reviews:
                dept = review.department.value
                bucket = dept_totals.setdefault(
                    dept,
                    {"pass": 0, "fail": 0, "checking": 0, "needs_info": 0},
                )
                bucket[review.status.value] = bucket.get(review.status.value, 0) + 1
                if review.status == ReviewStatus.FAIL:
                    failed_department_reviews += 1
                    push_alert(
                        "department_fail",
                        f"{review.department.value.title()} failed — {case.address}",
                        review.summary,
                        case.id,
                    )
                elif review.status == ReviewStatus.NEEDS_INFO:
                    push_alert(
                        "needs_info",
                        f"{review.department.value.title()} needs info — {case.address}",
                        review.summary,
                        case.id,
                    )

            for step in self.list_workflow_steps(case.id):
                if step.status == "interrupted":
                    interrupted_workflows += 1
                    push_alert(
                        "workflow_interrupted",
                        f"Workflow interrupted — {case.address}",
                        step.detail or "Distribution workflow can be resumed.",
                        case.id,
                        "distribution",
                    )
                elif step.status == "failed":
                    push_alert(
                        "workflow_failed",
                        f"Workflow step failed — {case.address}",
                        step.detail or step.name,
                        case.id,
                        "distribution",
                    )

            if case.status == CaseStatus.AWAITING_CLERK:
                responded_claims = [
                    claim
                    for claim in self.list_claims(case.id)
                    if claim.status == "resolved" and claim.response_message
                ]
                if responded_claims:
                    latest = max(responded_claims, key=lambda claim: claim.responded_at or claim.created_at)
                    push_alert(
                        "applicant_response",
                        f"Applicant responded — {case.address}",
                        latest.response_message or "Review the updated claim.",
                        case.id,
                        "claims",
                    )

        for task in open_tasks:
            if task.created_at < review_cutoff:
                case = case_by_id.get(task.case_id)
                address = case.address if case else task.title
                push_alert(
                    "overdue_task",
                    f"Overdue review — {address}",
                    task.title,
                    task.case_id,
                    "distribution",
                )

        department_rollup = [
            DashboardDepartmentRollup(
                department=dept,
                pass_count=counts.get("pass", 0),
                fail_count=counts.get("fail", 0),
                checking_count=counts.get("checking", 0),
                needs_info_count=counts.get("needs_info", 0),
            )
            for dept, counts in sorted(dept_totals.items())
        ]

        priority = {"overdue_task": 0, "workflow_interrupted": 1, "workflow_failed": 2, "department_fail": 3, "applicant_response": 4}
        alerts.sort(key=lambda item: (priority.get(item.kind, 9), item.title))

        return DashboardSummary(
            generated_at=now,
            open_tasks=len(open_tasks),
            overdue_tasks=overdue_tasks,
            unassigned_tasks=unassigned_tasks,
            my_tasks=my_tasks,
            awaiting_applicant=awaiting_applicant,
            awaiting_clerk=awaiting_clerk,
            in_review=in_review,
            stale_distribution=stale_distribution,
            interrupted_workflows=interrupted_workflows,
            failed_department_reviews=failed_department_reviews,
            cases_by_status=cases_by_status,
            department_rollup=department_rollup,
            alerts=alerts[:12],
        )

    def list_recent_activity(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        action: str | None = None,
    ) -> tuple[list[DashboardActivity], int]:
        all_cases = self.list_cases(limit=500)
        events: list[DashboardActivity] = []
        action_needle = action.strip().lower() if action else None

        for case in all_cases:
            for event in self.list_audit(case.id):
                if action_needle and event.action.lower() != action_needle:
                    continue
                events.append(
                    DashboardActivity(
                        id=event.id,
                        case_id=case.id,
                        address=case.address,
                        actor=event.actor,
                        action=event.action,
                        detail=event.detail,
                        at=event.at,
                    )
                )

        events.sort(key=lambda item: item.at, reverse=True)
        total = len(events)
        if offset:
            events = events[offset:]
        if limit > 0:
            events = events[:limit]
        return events, total

    def list_audit_actions(self) -> list[str]:
        seen: set[str] = set()
        for case in self.list_cases(limit=500):
            for event in self.list_audit(case.id):
                seen.add(event.action)
        return sorted(seen)
