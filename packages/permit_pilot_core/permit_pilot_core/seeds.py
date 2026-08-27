from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.models import CreateCaseRequest, Department, DepartmentStep
from permit_pilot_core.parcel import resolve_parcel
from permit_pilot_core.socrata.client import SocrataClient
from permit_pilot_core.settings import get_settings

REAL_NYC_CASES: list[CreateCaseRequest] = [
    CreateCaseRequest(
        address="43-30 PARSONS BOULEVARD, QUEENS",
        bbl="4051980021",
        bin="4117367",
        work_type="Construction Fence — Demolition of 3 story building",
        owner="FLUSHING HOSPITAL MEDICAL CENTER",
        borough="QUEENS",
    ),
    CreateCaseRequest(
        address="112-08 178 STREET, QUEENS",
        bbl="4103000034",
        bin="",
        work_type="Alteration",
        owner="",
        borough="QUEENS",
    ),
    CreateCaseRequest(
        address="761 MACON STREET, BROOKLYN",
        bbl="3014930048",
        bin="3040031",
        work_type="Plumbing modifications to existing kitchen",
        owner="",
        borough="BROOKLYN",
    ),
]


def _init_steps() -> list[DepartmentStep]:
    return [
        DepartmentStep(name="distribution", department=dept, status="pending")
        for dept in (
            Department.ZONING,
            Department.BUILDING,
            Department.FIRE,
            Department.UTILITIES,
            Department.LANDMARKS,
            Department.HOUSING,
            Department.CRITIC,
        )
    ]


async def ensure_seeded(store: FirestoreStore, engine: DistributionEngine) -> None:
    socrata = SocrataClient()
    existing = {c.bbl: c for c in store.list_cases()}
    bootstrap_clerk = get_settings().clerk_bootstrap_username

    for payload in REAL_NYC_CASES:
        resolved = await resolve_parcel(payload, socrata)
        case = existing.get(resolved.bbl)
        if case is None:
            case = store.create_case(resolved)
            existing[resolved.bbl] = case
            store.append_audit(
                case.id,
                actor="system",
                action="case_created",
                detail=f"Case created for BBL {case.bbl} with live NYC Open Data keys.",
            )

        store.save_workflow_steps(case.id, _init_steps())
        reviews = await engine.run_all(bbl=case.bbl, bin_=case.bin, work_type=case.work_type)
        store.save_distribution(case.id, reviews)
        steps = []
        for review in reviews:
            steps.append(
                DepartmentStep(
                    name="distribution",
                    department=review.department,
                    status="completed",
                    detail=review.summary,
                )
            )
        store.save_workflow_steps(case.id, steps)
        store.append_audit(
            case.id,
            actor="system",
            action="distribution_refreshed",
            detail=f"Seeded live NYC Open Data reviews for {len(reviews)} departments",
        )

        open_tasks = store.list_tasks(case.id, status="open")
        if not open_tasks:
            store.create_task(
                case.id,
                title=f"Review distribution — BIN {case.bin or case.bbl}",
                task_type="distribution_review",
                assignee=bootstrap_clerk or None,
            )
        else:
            for task in open_tasks:
                if not task.assignee and bootstrap_clerk:
                    store.assign_task(task.id, bootstrap_clerk)
