from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.models import Department, DepartmentReview, ReviewStatus
from permit_pilot_core.observability.traces import TraceRecorder


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class WorkflowStep(BaseModel):
    name: str
    department: Department | None = None
    status: StepStatus = StepStatus.PENDING
    detail: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None


WORKFLOW_DEPARTMENTS = [
    Department.ZONING,
    Department.BUILDING,
    Department.FIRE,
    Department.UTILITIES,
    Department.LANDMARKS,
    Department.HOUSING,
    Department.CRITIC,
]


def _now() -> datetime:
    return datetime.now(UTC)


class WorkflowRunner:
    def __init__(self, store: FirestoreStore, engine: DistributionEngine | None = None) -> None:
        self._store = store
        self._engine = engine or DistributionEngine()

    def init_steps(self, case_id: str) -> list[WorkflowStep]:
        steps = [
            WorkflowStep(name="distribution", department=dept, status=StepStatus.PENDING)
            for dept in WORKFLOW_DEPARTMENTS
        ]
        self._store.save_workflow_steps(case_id, steps)
        return steps

    def get_steps(self, case_id: str) -> list[WorkflowStep]:
        steps = self._store.list_workflow_steps(case_id)
        if not steps:
            return self.init_steps(case_id)
        return steps

    def mark_interrupted(self, case_id: str) -> WorkflowStep | None:
        steps = self.get_steps(case_id)
        for step in steps:
            if step.status == StepStatus.RUNNING:
                step.status = StepStatus.INTERRUPTED
                step.detail = "Worker interrupted — resume to continue"
                step.completed_at = _now()
                self._store.save_workflow_steps(case_id, steps)
                reviews = {r.department: r for r in self._store.list_distribution(case_id)}
                if step.department and step.department in reviews:
                    review = reviews[step.department]
                    review.status = ReviewStatus.CHECKING
                    self._store.save_distribution(case_id, list(reviews.values()))
                return step

        reviews = self._store.list_distribution(case_id)
        checking = next((r for r in reviews if r.status == ReviewStatus.CHECKING), None)
        if checking:
            for step in steps:
                if step.department == checking.department:
                    step.status = StepStatus.INTERRUPTED
                    step.detail = "Worker interrupted — resume to continue"
                    step.completed_at = _now()
                    self._store.save_workflow_steps(case_id, steps)
                    return step

        for step in steps:
            if step.status == StepStatus.PENDING:
                step.status = StepStatus.INTERRUPTED
                step.detail = "Worker interrupted — resume to continue"
                step.completed_at = _now()
                self._store.save_workflow_steps(case_id, steps)
                if step.department:
                    reviews_map = {r.department: r for r in reviews}
                    if step.department in reviews_map:
                        reviews_map[step.department].status = ReviewStatus.CHECKING
                        self._store.save_distribution(case_id, list(reviews_map.values()))
                return self.get_steps(case_id)[steps.index(step)]
        return None

    def _reset_terminal_steps(self, case_id: str) -> None:
        steps = self.get_steps(case_id)
        for step in steps:
            if step.status in {StepStatus.COMPLETED, StepStatus.FAILED}:
                step.status = StepStatus.PENDING
                step.started_at = None
                step.completed_at = None
                step.detail = ""
        self._store.save_workflow_steps(case_id, steps)

    async def run_next(self, case_id: str, *, bbl: str, bin_: str, work_type: str) -> WorkflowStep | None:
        steps = self.get_steps(case_id)
        if any(step.status == StepStatus.INTERRUPTED for step in steps):
            return None
        reviews = {r.department: r for r in self._store.list_distribution(case_id)}
        for step in steps:
            if step.status in {StepStatus.COMPLETED, StepStatus.FAILED}:
                continue
            if step.status == StepStatus.INTERRUPTED:
                step.status = StepStatus.RUNNING
            elif step.status == StepStatus.PENDING:
                step.status = StepStatus.RUNNING
                step.started_at = _now()
            dept = step.department
            if dept is None:
                continue
            self._mark_checking(case_id, dept, reviews)
            try:
                trace = TraceRecorder(self._store, case_id)
                with trace.span(
                    f"department.{dept.value}",
                    actor=dept.value,
                    detail=f"Running {dept.value} review",
                ):
                    review = await self._run_department(
                        dept, case_id=case_id, bbl=bbl, bin_=bin_, work_type=work_type
                    )
                reviews[dept] = review
                self._store.save_distribution(case_id, list(reviews.values()))
                latest_steps = self.get_steps(case_id)
                latest = next((s for s in latest_steps if s.department == dept), step)
                if latest.status == StepStatus.INTERRUPTED:
                    return latest
                step.status = StepStatus.COMPLETED
                step.completed_at = _now()
                step.detail = review.summary
                self._store.save_workflow_steps(case_id, latest_steps)
                self._store.append_audit(
                    case_id,
                    actor=dept.value,
                    action="workflow_step_completed",
                    detail=review.summary,
                )
                return step
            except Exception as exc:  # noqa: BLE001 — persist workflow failure for clerk visibility
                step.status = StepStatus.FAILED
                step.detail = str(exc)
                step.completed_at = _now()
                self._store.save_workflow_steps(case_id, steps)
                return step
        return None

    def _mark_checking(
        self,
        case_id: str,
        dept: Department,
        reviews: dict[Department, DepartmentReview],
    ) -> None:
        placeholder = DepartmentReview(
            department=dept,
            status=ReviewStatus.CHECKING,
            summary=f"Running {dept.value} review against NYC Open Data…",
            updated_at=_now(),
        )
        reviews[dept] = placeholder
        self._store.save_distribution(case_id, list(reviews.values()))

    async def resume_next(self, case_id: str, *, bbl: str, bin_: str, work_type: str) -> WorkflowStep | None:
        """Resume after an interrupted step — clears interrupted status and runs one department."""
        steps = self.get_steps(case_id)
        for step in steps:
            if step.status == StepStatus.INTERRUPTED:
                step.status = StepStatus.PENDING
                step.detail = ""
                step.completed_at = None
                self._store.save_workflow_steps(case_id, steps)
                break
        return await self.run_next(case_id, bbl=bbl, bin_=bin_, work_type=work_type)

    async def run_all(
        self,
        case_id: str,
        *,
        bbl: str,
        bin_: str,
        work_type: str,
        force: bool = False,
    ) -> list[WorkflowStep]:
        if force:
            self._reset_terminal_steps(case_id)
        completed: list[WorkflowStep] = []
        while True:
            if any(s.status == StepStatus.INTERRUPTED for s in self.get_steps(case_id)):
                break
            step = await self.run_next(case_id, bbl=bbl, bin_=bin_, work_type=work_type)
            if step is None:
                break
            completed.append(step)
            if step.status == StepStatus.FAILED:
                break
        return completed

    async def refresh_departments(
        self,
        case_id: str,
        departments: list[Department],
        *,
        bbl: str,
        bin_: str,
        work_type: str,
    ) -> list[DepartmentReview]:
        """Re-run selected department reviews without advancing the full workflow."""
        reviews = {r.department: r for r in self._store.list_distribution(case_id)}
        for dept in departments:
            self._mark_checking(case_id, dept, reviews)
            review = await self._run_department(
                dept, case_id=case_id, bbl=bbl, bin_=bin_, work_type=work_type
            )
            reviews[dept] = review
        self._store.save_distribution(case_id, list(reviews.values()))
        return list(reviews.values())

    async def _run_department(
        self, dept: Department, *, case_id: str, bbl: str, bin_: str, work_type: str
    ) -> DepartmentReview:
        if dept == Department.ZONING:
            return await self._engine.review_zoning(bbl=bbl)
        if dept == Department.BUILDING:
            return await self._engine.review_building(bbl=bbl, bin_=bin_)
        if dept == Department.FIRE:
            return await self._engine.review_fire(bin_=bin_)
        if dept == Department.UTILITIES:
            return await self._engine.review_utilities(bbl=bbl, bin_=bin_)
        if dept == Department.LANDMARKS:
            return await self._engine.review_landmarks(bbl=bbl, work_type=work_type)
        if dept == Department.HOUSING:
            return await self._engine.review_housing(bin_=bin_)
        if dept == Department.CRITIC:
            existing = [r for r in self._store.list_distribution(case_id) if r.department != Department.CRITIC]
            if len(existing) < len(WORKFLOW_DEPARTMENTS) - 1:
                existing = await self._engine.run_departments(bbl=bbl, bin_=bin_, work_type=work_type)
            return await self._engine.review_critic(reviews=existing)
        raise ValueError(f"Unknown department: {dept}")
