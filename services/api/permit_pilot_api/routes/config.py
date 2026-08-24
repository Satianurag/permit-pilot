from typing import Annotated

from fastapi import APIRouter, Depends

from permit_pilot_api.auth import get_current_user
from permit_pilot_api.config import gcp_project_id, observability_links

router = APIRouter(tags=["config"], dependencies=[Depends(get_current_user)])


@router.get("/config/observability")
def get_observability(case_id: str | None = None):
    return observability_links(case_id=case_id, project_id=gcp_project_id())
