from fastapi import APIRouter

from permit_pilot_api.config import gcp_project_id, observability_links

router = APIRouter(tags=["config"])


@router.get("/config/observability")
def get_observability(case_id: str | None = None):
    return observability_links(case_id=case_id, project_id=gcp_project_id())
