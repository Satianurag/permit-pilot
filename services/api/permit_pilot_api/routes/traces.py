from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from permit_pilot_core.models import TraceFeed
from permit_pilot_api.auth import get_current_user
from permit_pilot_api.config import gcp_project_id, observability_links
from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/traces", tags=["traces"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_traces(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100, description="Max runs to return")] = 20,
) -> TraceFeed:
    store = store_from_request(request)
    runs, total = store.list_recent_traces(limit=limit)
    return TraceFeed(
        runs=runs,
        total=total,
        observability=observability_links(case_id=None, project_id=gcp_project_id()),
    )
