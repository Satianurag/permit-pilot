from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ReviewStatus(StrEnum):
    CHECKING = "checking"
    PASS = "pass"
    FAIL = "fail"
    NEEDS_INFO = "needs_info"


class CaseStatus(StrEnum):
    IN_REVIEW = "in_review"
    AWAITING_CLERK = "awaiting_clerk"
    AWAITING_APPLICANT = "awaiting_applicant"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


class Department(StrEnum):
    ZONING = "zoning"
    BUILDING = "building"
    FIRE = "fire"
    UTILITIES = "utilities"
    LANDMARKS = "landmarks"
    HOUSING = "housing"
    CRITIC = "critic"


class EvidenceItem(BaseModel):
    source: str
    dataset_id: str
    label: str
    value: Any


class Citation(BaseModel):
    code: str
    excerpt: str
    source_url: str | None = None


class ObjectionStatus(StrEnum):
    OPEN = "open"
    NEW = "new"
    RESOLVED = "resolved"
    WITHDRAWN = "withdrawn"


class ObjectionItem(BaseModel):
    """One numbered, code-citing objection in DOB NOW first-review form."""

    obj_no: int
    department: str = ""
    code: str
    description: str
    recommended_fix: str = ""
    status: ObjectionStatus = ObjectionStatus.OPEN
    generated_by: str = ""


class DepartmentReview(BaseModel):
    department: Department
    status: ReviewStatus
    summary: str
    findings: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    objections: list[ObjectionItem] = Field(default_factory=list)
    updated_at: datetime
    generated_by: str = ""
    model: str = ""

    def open_objections(self) -> list[ObjectionItem]:
        return [item for item in self.objections if item.status in {ObjectionStatus.OPEN, ObjectionStatus.NEW}]


class CompletenessScan(BaseModel):
    complete_enough: bool
    missing: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    checklist: str = ""
    generated_by: str = "completeness_scan"
    model: str = ""


class RoutingPlan(BaseModel):
    departments: list[str] = Field(default_factory=list)
    skipped: dict[str, str] = Field(default_factory=dict)
    include_critic: bool = True
    reason: str = ""
    histdist: str = ""
    demolition: bool = False
    generated_by: str = "permit_orchestrator"


class PendingHitl(BaseModel):
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    confirmed: bool = False


class Case(BaseModel):
    id: str
    address: str
    bbl: str
    bin: str
    work_type: str
    owner: str
    borough: str | None = None
    status: CaseStatus
    created_at: datetime
    updated_at: datetime


class CreateCaseRequest(BaseModel):
    address: str
    bbl: str
    bin: str
    work_type: str
    owner: str
    borough: str | None = None


class CaseUpdateRequest(BaseModel):
    address: str | None = None
    bbl: str | None = None
    bin: str | None = None
    work_type: str | None = None
    owner: str | None = None
    borough: str | None = None


class IntakeRequest(BaseModel):
    address: str
    bbl: str
    bin: str = ""
    work_type: str
    owner: str = ""
    borough: str | None = None
    packet_text: str = ""
    packet_filename: str | None = None
    packet_content_type: str | None = None
    plan_filename: str | None = None
    plan_content_type: str | None = None
    plan_pdf_base64: str | None = None


class Task(BaseModel):
    id: str
    case_id: str
    title: str
    task_type: str
    status: str
    assignee: str | None = None
    created_at: datetime


class Claim(BaseModel):
    id: str
    case_id: str
    message: str
    status: str
    response_message: str | None = None
    notification_channel: str | None = None
    notification_reference: str | None = None
    notified_at: datetime | None = None
    manual_dob_now_sent: bool = False
    created_at: datetime
    responded_at: datetime | None = None


class ClaimResponseRequest(BaseModel):
    message: str


class IntakeDocument(BaseModel):
    redacted_text: str
    pii_findings: list[str]
    stored_at: datetime
    filename: str | None = None
    content_type: str | None = None
    has_pdf: bool = False


class RelatedPermit(BaseModel):
    job_number: str | None = None
    work_type: str | None = None
    status: str | None = None
    filing_date: str | None = None


class ParcelContext(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    map_url: str | None = None
    zoning_district: str | None = None


class ClerkBriefing(BaseModel):
    summary: str
    model: str
    generated_at: datetime
    generated_by: str


class AuditEvent(BaseModel):
    id: str
    case_id: str
    actor: str
    action: str
    detail: str
    at: datetime


class DepartmentStep(BaseModel):
    name: str
    department: Department | None = None
    status: str = "pending"
    detail: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    session_id: str | None = None
    engine_id: str | None = None


class CaseBundle(BaseModel):
    case: Case
    distribution: list[DepartmentReview]
    claims: list[Claim]
    audit: list[AuditEvent]
    workflow: list[DepartmentStep]
    trace: list[Any]
    observability: dict[str, str | None]
    document: IntakeDocument | None = None
    related_permits: list[RelatedPermit] = Field(default_factory=list)
    parcel: ParcelContext | None = None
    briefing: ClerkBriefing | None = None
    memories: list[dict[str, Any]] = Field(default_factory=list)
    fleet_run_id: str | None = None
    routing_plan: RoutingPlan | None = None
    completeness: CompletenessScan | None = None
    interrupt_requested: bool = False
    pending_hitl: PendingHitl | None = None
    critic_iterations: int = 0


class CaseDecision(BaseModel):
    decision: str
    note: str
    override: bool = False


class DashboardAlert(BaseModel):
    id: str
    kind: str
    title: str
    detail: str
    case_id: str
    href: str


class DashboardDepartmentRollup(BaseModel):
    department: str
    pass_count: int = 0
    fail_count: int = 0
    checking_count: int = 0
    needs_info_count: int = 0


class DashboardActivity(BaseModel):
    id: str
    case_id: str
    address: str
    actor: str
    action: str
    detail: str
    at: datetime


class DashboardSummary(BaseModel):
    generated_at: datetime
    open_tasks: int
    overdue_tasks: int
    unassigned_tasks: int
    my_tasks: int
    awaiting_applicant: int
    awaiting_clerk: int
    in_review: int
    stale_distribution: int
    interrupted_workflows: int
    failed_department_reviews: int
    cases_by_status: dict[str, int]
    department_rollup: list[DashboardDepartmentRollup]
    alerts: list[DashboardAlert]


class ActivityFeed(BaseModel):
    items: list[DashboardActivity]
    total: int
    limit: int
    offset: int
    actions: list[str] = Field(default_factory=list)


class TraceRunSummary(BaseModel):
    case_id: str
    address: str
    root_span_id: str
    root_name: str
    status: str
    span_count: int
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: int | None = None
    spans: list[Any] = Field(default_factory=list)


class TraceFeed(BaseModel):
    runs: list[TraceRunSummary]
    total: int
    observability: dict[str, str | None]
