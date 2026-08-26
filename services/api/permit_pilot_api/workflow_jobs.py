from __future__ import annotations

import logging

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.workflow.runner import WorkflowRunner

logger = logging.getLogger(__name__)


async def run_distribution_background(
    *,
    case_id: str,
    bbl: str,
    bin_: str,
    work_type: str,
    project_id: str | None = None,
) -> None:
    """Advance the distribution workflow after intake returns to the client."""
    try:
        store = FirestoreStore(project_id=project_id)
        engine = DistributionEngine()
        runner = WorkflowRunner(store, engine)
        await runner.run_all(case_id, bbl=bbl, bin_=bin_, work_type=work_type)
    except Exception:
        logger.exception("Background distribution workflow failed for case %s", case_id)
