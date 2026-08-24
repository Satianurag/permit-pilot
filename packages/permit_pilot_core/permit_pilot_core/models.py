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
    INTAKE = "intake"
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


class DepartmentReview(BaseModel):
    department: Department
    status: ReviewStatus
    summary: str
    findings: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    updated_at: datetime


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


class IntakeRequest(BaseModel):
    address: str
    bbl: str
    bin: str = ""
    work_type: str
    owner: str = ""
    borough: str | None = None
    packet_text: str = ""


class Task(BaseModel):
    id: str
    case_id: str
    title: str
    task_type: str
    status: str
    created_at: datetime


class Claim(BaseModel):
    id: str
    case_id: str
    message: str
    status: str
    response_message: str | None = None
    created_at: datetime
    responded_at: datetime | None = None


class ClaimResponseRequest(BaseModel):
    message: str


class IntakeDocument(BaseModel):
    redacted_text: str
    pii_findings: list[str]
    stored_at: datetime


class AuditEvent(BaseModel):
    id: str
    case_id: str
    actor: str
    action: str
    detail: str
    at: datetime


class CaseBundle(BaseModel):
    case: Case
    distribution: list[DepartmentReview]
    claims: list[Claim]
    audit: list[AuditEvent]
    workflow: list[Any]
    trace: list[Any]
    observability: dict[str, str | None]
    document: IntakeDocument | None = None


class CaseDecision(BaseModel):
    decision: str
    note: str
