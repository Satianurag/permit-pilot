from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.models import CreateCaseRequest
from permit_pilot_core.socrata.client import SocrataClient

# Real NYC Open Data reference cases (BBL/BIN from live Socrata rows — not synthetic).
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


async def _resolve_bin(payload: CreateCaseRequest, socrata: SocrataClient) -> CreateCaseRequest:
    if payload.bin:
        return payload
    rows = await socrata.pluto_by_bbl(payload.bbl)
    if not rows:
        return payload
    bin_ = str(rows[0].get("bin") or "")
    return payload.model_copy(update={"bin": bin_})


async def ensure_seeded(store: FirestoreStore, engine: DistributionEngine) -> None:
    socrata = SocrataClient()
    existing = {c.bbl: c for c in store.list_cases()}

    for payload in REAL_NYC_CASES:
        resolved = await _resolve_bin(payload, socrata)
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

        reviews = await engine.run_all(
            bbl=case.bbl,
            bin_=case.bin,
            work_type=case.work_type,
        )
        store.save_distribution(case.id, reviews)

        open_tasks = store.list_tasks(case.id, status="open")
        if not open_tasks:
            store.create_task(
                case.id,
                title=f"Review distribution — BIN {case.bin or case.bbl}",
                task_type="distribution_review",
            )
